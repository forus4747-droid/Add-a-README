"""Day skill selection on TRAIN only (5-min data up to 2024-06-30). Four formulas declared in advance, no fitting.
Same rule: most periods with positive rank IC, ties by mean IC. -> results/04_day_walkforward.csv"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from lab.data import load_5min_long
from lab.score import day_targets, score
from final.day_features import build
X, cols = build(load_5min_long); X = X[X.date <= "2024-06-30"]; T = day_targets(load_5min_long); T = T[T.date <= "2024-06-30"]
V = {"D1_fade_first30": lambda x: -x.first30, "D2_fade_gap": lambda x: -x.gap,
     "D3_fade_move_since_prev_close": lambda x: -x.since_prev_close, "D4_follow_first30": lambda x: x.first30}
P = [(str(y), f"{y}-01-01", f"{y}-12-31") for y in range(2016, 2024)] + [("2024H1", "2024-01-01", "2024-06-30")]
rows = []
for lab, lo, hi in P:
    te = X[(X.date >= lo) & (X.date <= hi)]
    for k, f in V.items(): rows.append(dict(config=k, period=lab, **score(te[["symbol", "date"]].assign(score=f(te).values), T, (lo, hi), horizon=1)))
r = pd.DataFrame(rows); r.to_csv("results/04_day_walkforward.csv", index=False)
print(r.pivot(index="period", columns="config", values="rank_ic").round(4).to_string())
print(r.groupby("config").agg(mean_ic=("rank_ic", "mean"), min_ic=("rank_ic", "min"), periods_pos=("rank_ic", lambda x: int((x > 0).sum())), mean_t=("ic_tstat", "mean"), mean_spread=("top_minus_bottom", "mean"), mean_excess=("excess_net_ann", "mean")).round(5).to_string())
