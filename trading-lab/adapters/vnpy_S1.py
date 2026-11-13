"""S1 (opening-range breakout, 5-min) on vnpy_ctastrategy BacktestingEngine. Run from trading-lab/: PY adapters/vnpy_S1.py"""
import sys, os
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "adapters"))
from vnpy_common import *
from lab.data import load_5min, DOW


class S1(SizedTemplate):
    valid_days = {}          # day -> True if >= 78 bars (day length is a data fact, precomputed with pandas)
    author = "lab"

    def on_init(self):
        self.day = None; self.rh = None; self.rl = None; self.nbar = 0; self.traded = False

    def on_bar(self, bar):
        dt = bar.datetime
        day = dt.strftime("%Y-%m-%d"); hm = dt.hour * 60 + dt.minute
        if day != self.day:
            self.day = day; self.rh = -1e18; self.rl = 1e18; self.traded = False
        if not self.valid_days.get(day, False):
            return
        if hm < 600:                                   # 09:30..09:55 -> opening range
            self.rh = max(self.rh, bar.high_price); self.rl = min(self.rl, bar.low_price)
            return
        if self.pos == 0:
            # rule 2: bars 10:00..15:40, flat, no trade yet today (order sent this bar also counts)
            if hm <= 940 and not self.traded and bar.close_price > self.rh:
                self.send_buy(); self.traded = True
        else:
            # rule 3 (any bar up to 15:45) and rule 4 (15:50 bar -> sell at 15:55 open)
            if bar.close_price < self.rl or hm >= 950:
                self.send_sell()


if __name__ == "__main__":
    rows = []
    for sym in DOW:
        m = load_5min(sym).sort_values("time_new_york").reset_index(drop=True)
        n = m.groupby("day").open.size()
        S1.valid_days = {d: True for d in n.index[n >= 78]}
        dts = pd.to_datetime(m.time_new_york.values).to_pydatetime()   # naive New York local time
        bars = make_bars(sym, dts, m.open, m.high, m.low, m.close, m.volume, Interval.MINUTE)
        e = run_engine(sym, bars, Interval.MINUTE, S1, {}, dts[0], dts[-1])
        r, _ = round_trips(sym, e, "%Y-%m-%d %H:%M")
        rows += r; print(sym, len(r), flush=True)
    out = pd.DataFrame(rows, columns="symbol,entry_time,entry_price,exit_time,exit_price,shares,pnl_net".split(","))
    os.makedirs("results/trades", exist_ok=True)
    out.to_csv("results/trades/vnpy_S1.csv", index=False)
    print(len(out), out.pnl_net.sum())
