"""TRAIN-only (2016-2023) check: rank IC of each single feature vs the 5-day target, per year.
Writes results/04_feature_stability.csv. Used to see which ingredients are stable; nothing after 2023 is read."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from lab.data import load_daily
from lab.score import swing_targets
from final.features import build
daily = load_daily(); daily = daily[daily.date <= "2023-12-31"]
X, cols = build(daily); T = swing_targets(); T = T[T.target_end <= "2023-12-31"]
m = X.merge(T[["symbol", "date", "target"]], on=["symbol", "date"]); m["tr"] = m.groupby("date").target.rank(pct=True) - 0.5
m["year"] = m.date.str[:4]; rows = []
for f in cols:
    ic = (m[f] * m.tr).groupby(m.date).mean() * 12            # both are centred ranks: mean product*12 ~ Spearman
    y = ic.groupby(ic.index.str[:4]).mean()
    rows.append(dict(feature=f, mean_ic=ic.mean(), t_all=ic.mean() / ic.std() * np.sqrt(len(ic) / 5), years_same_sign=int((np.sign(y) == np.sign(ic.mean())).sum()), **{k: round(v, 4) for k, v in y.items()}))
r = pd.DataFrame(rows).sort_values("t_all", key=abs, ascending=False); r.to_csv("results/04_feature_stability.csv", index=False)
print(r.round(4).to_string(index=False))
