import sys, os, math
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "adapters"))
import backtrader as bt, pandas as pd
from lab.data import load_5min, DOW
from backtrader_common import run, Base

class S1(Base):
    params = dict(valid=None)
    def __init__(self):
        super().__init__(); self.day = None; self.traded = False; self.hi = None; self.lo = None
    def next_open(self):
        # current bar's open is the fill price; decisions use previous bar (index -1) only
        d = self.data; day = d.datetime.date(0); t = d.datetime.time(0); hm = t.strftime("%H:%M")
        if day != self.day:
            self.day = day; self.traded = False; self.hi = None; self.lo = None
        ok = day.isoformat() in self.p.valid
        if not ok or hm == "09:30": return
        ph = d.high[-1]; pl = d.low[-1]; pc = d.close[-1]
        phm = bt.num2date(d.datetime[-1]).strftime("%H:%M")
        if phm <= "09:55":
            self.hi = ph if self.hi is None else max(self.hi, ph)
            self.lo = pl if self.lo is None else min(self.lo, pl)
            return
        pos = self.position.size
        if hm == "15:55":
            if pos > 0: self.close()
            return
        if pos == 0 and not self.traded and phm <= "15:40" and pc > self.hi:
            self.buy(size=math.floor(10000 / d.open[0])); self.traded = True
        elif pos > 0 and pc < self.lo:
            self.close()

if __name__ == "__main__":
    res = []
    for s in DOW:
        m = load_5min(s)
        cnt = m.groupby("day").size(); valid = set(cnt[cnt >= 78].index)
        m["dt"] = pd.to_datetime(m.time_new_york)   # naive New York wall-clock, no tz conversion
        m = m.sort_values("dt")
        r = run(s, m, S1, "%Y-%m-%d %H:%M", bt.TimeFrame.Minutes, 5, valid=valid)
        res.append(r); print(s, len(r), flush=True)
    out = pd.concat(res); os.makedirs("results/trades", exist_ok=True)
    out[["symbol","entry_time","entry_price","exit_time","exit_price","shares","pnl_net"]].to_csv("results/trades/backtrader_S1.csv", index=False)
