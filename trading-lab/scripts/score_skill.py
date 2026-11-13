"""Fixed scorer for the prediction test. Usage: score_skill.py SKILL
Reads results/preds/SKILL_swing.parquet and/or SKILL_day.parquet, writes results/score_SKILL.csv."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from lab.score import swing_targets, day_targets, score, verdict
k = sys.argv[1]; rows = []
W = {"swing": (swing_targets, 5, {"DEV": ("2024-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31")}),
     "day": (day_targets, 1, {"DEV": ("2024-07-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31")})}
for task, (tf, h, splits) in W.items():
    f = f"results/preds/{k}_{task}.parquet"
    if not os.path.exists(f): continue
    p = pd.read_parquet(f)[["symbol", "date", "score"]]; p["date"] = p.date.astype(str).str[:10]
    assert not p.duplicated(["symbol", "date"]).any(), "duplicate (symbol,date) rows"
    assert p.date.max() <= "2025-12-31"
    T = tf()
    for sp, r in splits.items():
        m = score(p, T, r, horizon=h); rows.append(dict(task=task, skill=k, split=sp, **m, verdict=verdict(m)))
r = pd.DataFrame(rows); r.to_csv(f"results/score_{k}.csv", index=False); print(r.to_string(index=False))
