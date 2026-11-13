"""No-look-ahead proof for the final skill: recompute scores from data cut off at the date and compare."""
import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from lab.data import load_daily, load_5min_long
from final.skill import swing_scores, day_scores
rng = np.random.default_rng(11); out = {}
daily = load_daily(); full = pd.read_parquet("results/preds/final_swing.parquet"); res = []
for dt in rng.choice(sorted(full.date.unique()), 5, replace=False):
    t = swing_scores(daily[daily.date <= dt]); t = t[t.date == dt].merge(full[full.date == dt], on=["symbol", "date"])
    res.append(dict(date=dt, stocks=len(t), max_abs_diff=float((t.score_x - t.score_y).abs().max())))
out["swing"] = res
fd = pd.read_parquet("results/preds/final_day.parquet"); res = []
for dt in rng.choice(sorted(fd.date.unique()), 5, replace=False):
    def cut(sym, dt=dt):
        m = load_5min_long(sym); m = m[(m.day < dt) | ((m.day == dt) & (m.hm <= "09:55"))]
        # pad the cut day to 78 rows with copies of its last known bar so the 'full day' filter keeps it; values after 09:55 are never read
        last = m[m.day == dt]
        if len(last):
            pad = pd.concat([last.iloc[[-1]]] * (78 - len(last))).assign(hm="23:59"); m = pd.concat([m, pad], ignore_index=True)
        return m
    t = day_scores(cut); t = t[t.date == dt].merge(fd[fd.date == dt], on=["symbol", "date"])
    res.append(dict(date=dt, stocks=len(t), max_abs_diff=float((t.score_x - t.score_y).abs().max())))
out["day"] = res
json.dump(out, open("results/04_final_truncation.json", "w"), indent=1); print(json.dumps(out, indent=1))
