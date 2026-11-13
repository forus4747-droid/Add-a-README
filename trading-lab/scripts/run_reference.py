import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from lab.data import DOW, load_5min, daily_from_5min
from reference.ref_backtest import s1_orb, s2_sma
t1, t2 = [], []
for s in DOW:
    t1 += s1_orb(s, load_5min(s).to_dict("records")); t2 += s2_sma(s, daily_from_5min(s).to_dict("records"))
for n, t in (("S1", t1), ("S2", t2)):
    d = pd.DataFrame(t); d.to_csv(f"results/trades/reference_{n}.csv", index=False)
    print(n, "trades", len(d), "net pnl", round(d.pnl_net.sum(), 2), "win rate", round((d.pnl_net > 0).mean(), 4))
