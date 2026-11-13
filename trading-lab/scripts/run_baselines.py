"""Baselines every skill must beat. Writes results/preds/baseline_*.parquet and results/02_baselines.csv"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from lab.data import load_daily, load_5min, DOW
from lab.score import swing_targets, day_targets, score, verdict
rows = []
# ---- swing baselines
d = load_daily(stocks_only=True).sort_values(["symbol", "date"]); g = d.groupby("symbol").close
rng = np.random.default_rng(0)
B = {"random": pd.Series(rng.standard_normal(len(d)), index=d.index),
     "momentum_12_1": g.shift(21) / g.shift(252) - 1,
     "reversal_5d": -(d.close / g.shift(5) - 1)}
T = swing_targets()
for k, s in B.items():
    p = d[["symbol", "date"]].assign(score=s).dropna(); p.to_parquet(f"results/preds/baseline_swing_{k}.parquet", index=False)
    for sp in ("DEV", "VAL"):
        m = score(p, T, sp); rows.append(dict(task="swing", skill=k, split=sp, **m, verdict=verdict(m)))
# ---- day baselines: first-30-min return (momentum) and its negative (reversal)
out = []
for sym in DOW:
    m = load_5min(sym); a = m[m.hm == "09:30"].set_index("day").open; b = m[m.hm == "09:55"].set_index("day").close
    out.append(pd.DataFrame({"symbol": sym, "date": a.index, "or_ret": (b / a - 1).reindex(a.index).values}))
o = pd.concat(out).dropna(); TD = day_targets()
DB = {"random": rng.standard_normal(len(o)), "first30_momentum": o.or_ret.values, "first30_reversal": -o.or_ret.values}
for k, s in DB.items():
    p = o[["symbol", "date"]].assign(score=s); p.to_parquet(f"results/preds/baseline_day_{k}.parquet", index=False)
    for sp, rngd in (("DEV", ("2024-07-01", "2024-12-31")), ("VAL", ("2025-01-01", "2025-12-31"))):
        m = score(p, TD, rngd, horizon=1); rows.append(dict(task="day", skill=k, split=sp, **m, verdict=verdict(m)))
r = pd.DataFrame(rows); r.to_csv("results/02_baselines.csv", index=False)
print(r.drop(columns=["coverage", "days"]).to_string(index=False))
