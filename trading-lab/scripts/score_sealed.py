"""Step 5 scorer: the same lab.score functions, on the sealed window. Run with LAB_DATA=.../data_sealed.
Also scores three reference points for context: random, 12-1 momentum, and (day) following the first 30 min."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from lab.data import load_daily, load_5min_long, DATA
from lab.score import swing_targets, day_targets, score, verdict
assert DATA.endswith("data_sealed"); W = ("2026-01-01", "2026-11-12"); rows = []
TS, TD = swing_targets(), day_targets(load_5min_long)
fs = pd.read_parquet("results/preds/final_sealed_swing.parquet"); fd = pd.read_parquet("results/preds/final_sealed_day.parquet")
d = load_daily(stocks_only=True).sort_values(["symbol", "date"]); g = d.groupby("symbol").close; rng = np.random.default_rng(0)
refs = {"swing": {"FINAL SKILL": fs, "random": d[["symbol", "date"]].assign(score=rng.standard_normal(len(d))),
                  "momentum 12-1": d[["symbol", "date"]].assign(score=(g.shift(21) / g.shift(252) - 1).values).dropna()},
        "day": {"FINAL SKILL": fd, "random": fd.assign(score=rng.standard_normal(len(fd))), "follow first 30 min": fd.assign(score=-fd.score)}}
for task, T, h in (("swing", TS, 5), ("day", TD, 1)):
    for k, p in refs[task].items():
        m = score(p, T, W, horizon=h); rows.append(dict(task=task, skill=k, **m, verdict=verdict(m)))
r = pd.DataFrame(rows); r.to_csv("results/05_sealed_scores.csv", index=False); print(r.drop(columns=["coverage"]).to_string(index=False))
