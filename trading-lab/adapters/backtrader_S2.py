import sys, os, math
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "adapters"))
import backtrader as bt, pandas as pd
from lab.data import daily_from_5min, DOW
from backtrader_common import run, Base

class S2(Base):
    def __init__(self):
        super().__init__()
        self.f = bt.ind.SMA(self.data.close, period=20)
        self.s = bt.ind.SMA(self.data.close, period=50)
        self.nopen = 0
    def next_open(self):
        # Decision from previous bar (t) and the one before (t-1); fill at current bar (t+1) open.
        d = self.data
        if len(d) < 51: return
        f1, s1, f2, s2 = self.f[0], self.s[0], self.f[-1], self.s[-1]
        if self.position.size == 0:
            if f1 > s1 and f2 <= s2: self.buy(size=math.floor(10000 / d.open[0]), coc=False)
        elif f1 < s1:
            self.close(coc=False)
    def next(self):
        if len(self.data) == self.data.buflen() and self.position.size > 0:
            self.close()   # cheat-on-close: fills at the last bar's close

if __name__ == "__main__":
    res = []
    for s in DOW:
        m = daily_from_5min(s); m["dt"] = pd.to_datetime(m.date); m = m.sort_values("dt")
        r = run(s, m, S2, "%Y-%m-%d", bt.TimeFrame.Days, 1, coc=True)
        res.append(r); print(s, len(r), flush=True)
    out = pd.concat(res); os.makedirs("results/trades", exist_ok=True)
    out[["symbol","entry_time","entry_price","exit_time","exit_price","shares","pnl_net"]].to_csv("results/trades/backtrader_S2.csv", index=False)
