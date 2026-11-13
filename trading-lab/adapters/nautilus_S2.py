import sys, os, math
sys.path.insert(0, os.getcwd())
import pandas as pd
from multiprocessing import Pool
from adapters.nautilus_common import *
from lab.data import load_5min, DOW

SPEC = BarSpecification(1, BarAggregation.DAY, PriceType.LAST)

class S2(Base):
    def on_start(self):
        super().on_start(); self.closes = []

    def on_bar(self, b):
        self.closes.append(float(b.close)); n = len(self.closes)
        if n < 51: return
        s20 = sum(self.closes[-20:]) / 20; s50 = sum(self.closes[-50:]) / 50
        p20 = sum(self.closes[-21:-1]) / 20; p50 = sum(self.closes[-51:-1]) / 50
        if self.flat() and s20 > s50 and p20 <= p50: self.pending = "buy"
        elif (not self.flat()) and s20 < s50: self.pending = "sell"

    def on_quote_tick(self, q):
        final = (q.ts_event == self.final_ts)      # synthetic quote = last day's close
        if self.pending == "buy" and self.flat() and not final:
            qty = math.floor(10000 / float(q.ask_price))
            if qty > 0: self.order(OrderSide.BUY, qty)
        elif (self.pending == "sell" or final) and not self.flat():
            self.order(OrderSide.SELL, int(self.portfolio.net_position(self.inst.id)))
        self.pending = None

def work(sym):
    m = load_5min(sym)
    m["t"] = pd.to_datetime(m.time_utc, utc=True).dt.as_unit("ns").astype("int64")
    g = m.groupby("day")
    d = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(),
                      "volume": g.volume.sum(), "t_open": g.t.first(), "t_close": g.t.last() + NS5}).reset_index()
    inst = make_instrument(sym)
    bt = BarType(inst.id, SPEC, AggregationSource.EXTERNAL)
    bars, quotes = [], []
    for r in d.itertuples(index=False):
        bars.append(bar(inst, bt, r.open, r.high, r.low, r.close, r.volume, int(r.t_close)))
        quotes.append(quote(inst, r.open, int(r.t_open) + 1))   # day-open quote
    final_ts = int(d.t_close.iloc[-1]) + 1
    quotes.append(quote(inst, d.close.iloc[-1], final_ts))        # last day's close quote (protocol rule 4)
    res = run_symbol(S2, sym, bars, quotes, None, bt, final_ts)
    ny = lambda ns: pd.Timestamp(ns, unit="ns", tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d")
    return [dict(symbol=sym, entry_time=ny(r["entry_ts"]), entry_price=r["entry_price"], exit_time=ny(r["exit_ts"]),
                 exit_price=r["exit_price"], shares=r["shares"], pnl_net=r["pnl_net"]) for r in res]

if __name__ == "__main__":
    syms = DOW if len(sys.argv) < 2 else sys.argv[1:]
    with Pool(4) as p: allr = p.map(work, syms)
    df = pd.DataFrame([r for rs in allr for r in rs], columns="symbol,entry_time,entry_price,exit_time,exit_price,shares,pnl_net".split(","))
    os.makedirs("results/trades", exist_ok=True)
    df.to_csv("results/trades/nautilus_S2.csv" if len(syms) == len(DOW) else "/tmp/nautilus_S2_test.csv", index=False)
    print(len(df), df.pnl_net.sum())
