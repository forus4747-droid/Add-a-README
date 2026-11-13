import sys, os
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd, vectorbt as vbt
from lab.data import load_5min, DOW
FEE = 0.0005
out = []
for sym in DOW:
    d = load_5min(sym).reset_index(drop=True)
    cnt = d.groupby("day").hm.transform("size")
    ok = (cnt >= 78).values
    orb = d[d.hm.between("09:30", "09:55")].groupby("day").agg(rh=("high", "max"), rl=("low", "min"))
    d = d.join(orb, on="day")
    inwin = d.hm.between("10:00", "15:40").values & ok
    up = inwin & (d.close > d.rh).values
    # rule 3 (stop) has no time window of its own: any bar from 10:00 up to 15:50 (a 15:55 close would execute next day)
    dn = d.hm.between("10:00", "15:50").values & ok & (d.close < d.rl).values
    # first breakout bar of the day (one trade per day); later signals not generated
    first_up = up & (pd.Series(up).groupby(d.day.values).cumsum().values == 1)
    # signals decided on close of bar i -> executed at open of bar i+1 (same day: signals only up to 15:40)
    entries = pd.Series(first_up).shift(1, fill_value=False).values
    stops = pd.Series(dn).shift(1, fill_value=False).values
    force = ((d.hm == "15:55").values) & ok       # decided/executed at the 15:55 bar's own open
    exits = stops | force
    idx = pd.DatetimeIndex(d.time_new_york)
    op = pd.Series(d.open.values, index=idx)
    size = pd.Series(np.floor(10000 / d.open.values), index=idx)
    pf = vbt.Portfolio.from_signals(op, entries=pd.Series(entries, index=idx), exits=pd.Series(exits, index=idx),
        price=op, size=size, size_type="amount", fees=FEE, init_cash=1e9, direction="longonly",
        accumulate=False, freq="5min")
    t = pf.trades.records_readable
    for _, r in t.iterrows():
        assert r["Status"] == "Closed", (sym, r)
        out.append(dict(symbol=sym, entry_time=r["Entry Timestamp"].strftime("%Y-%m-%d %H:%M"),
            entry_price=r["Avg Entry Price"], exit_time=r["Exit Timestamp"].strftime("%Y-%m-%d %H:%M"),
            exit_price=r["Avg Exit Price"], shares=int(round(r["Size"])), pnl_net=r["PnL"]))
os.makedirs("results/trades", exist_ok=True)
pd.DataFrame(out).to_csv("results/trades/vectorbt_S1.csv", index=False)
print(len(out), "trades")
