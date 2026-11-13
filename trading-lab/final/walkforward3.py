"""Round 3, TRAIN only (2016-2023): four reversal formulas declared in advance (no fitting at all).
Selection rule fixed beforehand: most years with positive rank IC, ties broken by mean IC. -> results/04_walkforward3.csv"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from lab.data import load_daily
from lab.score import swing_targets, score
from final.features import build
daily = load_daily(); daily = daily[daily.date <= "2023-12-31"]; X, cols = build(daily); T = swing_targets()
V = {"V1_rev_1_2_5": lambda x: -(x.ret1 + x.ret2 + x.ret5) / 3,
     "V2_rev5_volscaled": lambda x: -x.ret5_vs,
     "V3_rev_residual": lambda x: -(x.res_ret5 + x.ret1 + x.ret2) / 3,
     "V4_rev_plus_momentum": lambda x: -(x.ret1 + x.ret2 + x.ret5) / 3 + 0.5 * x.mom_12_1}
rows = []
for Y in range(2016, 2024):
    te = X[(X.date >= f"{Y}-01-01") & (X.date <= f"{Y}-12-31")]
    for k, f in V.items(): rows.append(dict(config=k, year=Y, **score(te[["symbol", "date"]].assign(score=f(te).values), T, (f"{Y}-01-01", f"{Y}-12-31"))))
r = pd.DataFrame(rows); r.to_csv("results/04_walkforward3.csv", index=False)
print(r.pivot(index="year", columns="config", values="rank_ic").round(4).to_string())
s = r.groupby("config").agg(mean_ic=("rank_ic", "mean"), min_ic=("rank_ic", "min"), years_pos=("rank_ic", lambda x: int((x > 0).sum())), mean_t=("ic_tstat", "mean"), mean_excess=("excess_net_ann", "mean"), years_excess_pos=("excess_net_ann", lambda x: int((x > 0).sum())), mean_hit=("hit_rate", "mean"))
print(s.round(4).to_string())
