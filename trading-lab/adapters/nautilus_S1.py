import sys, os, math
sys.path.insert(0, os.getcwd())
import pandas as pd
from multiprocessing import Pool
from adapters.nautilus_common import *
from lab.data import load_5min, DOW

BT = BarType(InstrumentId(Symbol("X"), VENUE), BarSpecification(5, BarAggregation.MINUTE, PriceType.LAST), AggregationSource.EXTERNAL)

class S1(Base):
    def on_start(self):
        super().on_start()
        self.hi = self.lo = None; self.traded = False; self.day = None

    def on_bar(self, b):
        day, hm = self.meta[b.ts_event]        # metadata of the bar: NY day, NY open hm, day bar-count ok
        if day[0] != self.day:
            self.day = day[0]; self.hi = -1e18; self.lo = 1e18; self.traded = False
        if not day[1]:
            return
        c = float(b.close)
        if "09:30" <= hm <= "09:55":
            self.hi = max(self.hi, float(b.high)); self.lo = min(self.lo, float(b.low))
        elif "10:00" <= hm <= "15:40":
            if self.flat() and not self.traded and c > self.hi:
                self.pending = "buy"
            elif (not self.flat()) and c < self.lo:
                self.pending = "sell"

    def on_quote_tick(self, q):
        hm = self.meta[q.ts_event][1] if q.ts_event in self.meta else None
        if hm is None: return
        if self.day is None or not self.meta[q.ts_event][0][1]: self.pending = None; return
        if self.pending == "buy" and self.flat():
            qty = math.floor(10000 / float(q.ask_price)); self.traded = True
            if qty > 0: self.order(OrderSide.BUY, qty)
        elif self.pending == "sell" and not self.flat():
            self.order(OrderSide.SELL, int(self.portfolio.net_position(self.inst.id)))
        elif hm == "15:55" and not self.flat():
            self.order(OrderSide.SELL, int(self.portfolio.net_position(self.inst.id)))
        self.pending = None

def work(sym):
    m = load_5min(sym)
    inst = make_instrument(sym)
    bt = BarType(inst.id, BT.spec, AggregationSource.EXTERNAL)
    t = pd.to_datetime(m.time_utc, utc=True).dt.as_unit("ns").astype("int64").values  # open time ns (UTC)
    cnt = m.groupby("day").day.transform("size").values
    bars, quotes, meta = [], [], {}
    for i, r in enumerate(m.itertuples(index=False)):
        ok = cnt[i] >= 78
        cts = int(t[i]) + NS5
        bars.append(bar(inst, bt, r.open, r.high, r.low, r.close, r.volume, cts))
        quotes.append(quote(inst, r.open, int(t[i]) + 1))     # open quote at open_time+1ns (after previous bar close)
        meta[cts] = ((r.day, ok), r.hm)
        meta[int(t[i]) + 1] = ((r.day, ok), r.hm)
    # bar meta keyed by close ts; hm of the bar's own open
    for i, r in enumerate(m.itertuples(index=False)):
        meta[int(t[i]) + NS5] = ((r.day, cnt[i] >= 78), r.hm)
    # NOTE: bar close (open+5min) and next bar's quote (open+5min... stamped +1ns) never collide in meta keys
    res = run_symbol(S1, sym, bars, quotes, meta, bt)
    ny = lambda ns: pd.Timestamp(ns, unit="ns", tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d %H:%M")
    rows = []
    for r in res:
        rows.append(dict(symbol=sym, entry_time=ny(r["entry_ts"]), entry_price=r["entry_price"], exit_time=ny(r["exit_ts"]),
                         exit_price=r["exit_price"], shares=r["shares"], pnl_net=r["pnl_net"]))
    return rows

if __name__ == "__main__":
    syms = DOW if len(sys.argv) < 2 else sys.argv[1:]
    with Pool(4) as p: allr = p.map(work, syms)
    df = pd.DataFrame([r for rs in allr for r in rs], columns="symbol,entry_time,entry_price,exit_time,exit_price,shares,pnl_net".split(","))
    os.makedirs("results/trades", exist_ok=True)
    df.to_csv("results/trades/nautilus_S1.csv" if len(syms) == len(DOW) else "/tmp/nautilus_S1_test.csv", index=False)
    print(len(df), df.pnl_net.sum())
