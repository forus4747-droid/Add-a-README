"""Fixed scorer for skills that emit discrete buy/sell signals instead of a ranking score (protocol extension,
added before any such skill was scored except aihf_statarb, which could not be ranked).
Usage: score_signals.py SKILL swing|bar
 swing: results/preds/SKILL_swing.parquet  [symbol,date,score]      sign(score) = +1 buy / -1 sell / 0 none
        outcome = open[t+1] -> open[t+6] return
 bar:   results/preds/SKILL_bar.parquet    [symbol,time,score]      time = 'YYYY-MM-DD HH:MM' New York bar time
        outcome = next bar's open -> same day's 15:55 open (signals on the 15:50/15:55 bars are ignored)
For each split: n signals; mean outcome after buy (and sell) signals MINUS the mean outcome of all stocks at the
same time (so a rising market does not count as skill); t-stat over days; share of signals that beat that mean.
Verdict: PREDICTS if buy-excess t-stat > 2 and buy-excess mean > round-trip cost (0.1%)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from lab.data import DOW, load_5min
from lab.score import swing_targets, COST_RT
k, mode = sys.argv[1], sys.argv[2]
if mode == "swing":
    T = swing_targets().rename(columns={"date": "t"}); T["day"] = T.t; T["end"] = T.target_end
    P = pd.read_parquet(f"results/preds/{k}_swing.parquet").rename(columns={"date": "t"})
    SP = {"DEV": ("2024-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31")}
else:
    out = []
    for s in DOW:
        m = load_5min(s); n = m.groupby("day").size(); m = m[m.day.isin(n[n == 78].index)].copy()
        m["nxt"] = m.groupby("day").open.shift(-1); m["eod"] = m.day.map(m[m.hm == "15:55"].set_index("day").open)
        m = m[m.hm < "15:50"]; out.append(pd.DataFrame({"symbol": s, "t": m.time_new_york, "day": m.day, "end": m.day, "target": m.eod / m.nxt - 1}))
    T = pd.concat(out); P = pd.read_parquet(f"results/preds/{k}_bar.parquet").rename(columns={"time": "t"})
    SP = {"DEV": ("2024-07-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31")}
P["t"] = P.t.astype(str); assert not P.duplicated(["symbol", "t"]).any()
x = T.merge(P[["symbol", "t", "score"]], on=["symbol", "t"], how="left").fillna({"score": 0})
x["excess"] = x.target - x.groupby("t").target.transform("mean"); rows = []
for sp, (lo, hi) in SP.items():
    g = x[(x.day >= lo) & (x.end <= hi)]
    for side, sel in (("buy", g.score > 0), ("sell", g.score < 0)):
        e = g[sel]; d = e.groupby("day").excess.mean(); n = len(e)
        if n < 30 or len(d) < 10: rows.append(dict(skill=k, mode=mode, split=sp, side=side, signals=n, verdict="too few signals")); continue
        t = d.mean() / d.std(ddof=1) * np.sqrt(len(d) / (5 if mode == "swing" else 1)); sgn = 1 if side == "buy" else -1
        rows.append(dict(skill=k, mode=mode, split=sp, side=side, signals=n, signal_days=len(d), mean_outcome=round(e.target.mean(), 5),
            mean_excess=round(e.excess.mean(), 5), tstat=round(t, 2), beat_rate=round((sgn * e.excess > 0).mean(), 4),
            verdict="PREDICTS" if (sgn * t > 2 and sgn * e.excess.mean() > COST_RT) else "no proven edge"))
r = pd.DataFrame(rows); r.to_csv(f"results/signals_{k}_{mode}.csv", index=False); print(r.to_string(index=False))
