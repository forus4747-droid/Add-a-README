"""Scoring harness for the prediction test (PROTOCOL §3 P). One function scores every skill the same way."""
import numpy as np, pandas as pd
from .data import SPLITS, DOW, load_daily, load_5min
COST_RT = 0.001  # 0.05% per side

def swing_targets():
    """target for (symbol, date t) = open[t+6]/open[t+1]-1 ; known only after t+6. Stocks only."""
    d = load_daily(stocks_only=True).sort_values(["symbol", "date"])
    g = d.groupby("symbol").open
    d["target"] = g.shift(-6) / g.shift(-1) - 1
    d["target_end"] = d.groupby("symbol").date.shift(-6)
    return d[["symbol", "date", "target", "target_end"]].dropna()

def day_targets(loader=load_5min):
    """Dow 30. target for (symbol, day) = open of 15:55 bar / open of 10:00 bar - 1. Full 78-bar days only."""
    out = []
    for s in DOW:
        m = loader(s); n = m.groupby("day").size(); m = m[m.day.isin(n[n == 78].index)]
        a = m[m.hm == "10:00"].set_index("day").open; b = m[m.hm == "15:55"].set_index("day").open
        out.append(pd.DataFrame({"symbol": s, "date": a.index, "target": (b / a - 1).values, "target_end": a.index}))
    return pd.concat(out, ignore_index=True)

def score(preds, targets, split, horizon=5, min_names=20):
    """preds: DataFrame[symbol,date,score]. Returns dict of metrics on `split` (target must end inside split)."""
    lo, hi = split if isinstance(split, tuple) else SPLITS[split]
    t = targets[(targets.date >= lo) & (targets.target_end <= hi)]
    x = t.merge(preds, on=["symbol", "date"], how="inner").dropna(subset=["score", "target"])
    ics, hits, spreads, tops, alls = [], [], [], [], []
    for _, g in x.groupby("date"):
        if len(g) < min_names or g.score.nunique() < 5: continue
        ics.append(g.score.rank().corr(g.target.rank()))
        hits.append(((g.score > g.score.median()) == (g.target > g.target.median())).mean())
        q = pd.qcut(g.score.rank(method="first"), 5, labels=False)
        tops.append(g.target[q == 4].mean()); spreads.append(g.target[q == 4].mean() - g.target[q == 0].mean()); alls.append(g.target.mean())
    n = len(ics); ics = np.array(ics); per_year = 252 / horizon
    if n == 0: return dict(days=0)
    return dict(days=n, coverage=round(len(x) / max(len(t), 1), 3), rank_ic=round(float(ics.mean()), 4),
        ic_tstat=round(float(ics.mean() / ics.std(ddof=1) * np.sqrt(n / horizon)), 2),
        hit_rate=round(float(np.mean(hits)), 4), top_minus_bottom=round(float(np.mean(spreads)), 5),
        top_q_net_ann=round(float((np.mean(tops) - COST_RT) * per_year), 4),
        equal_weight_ann=round(float(np.mean(alls) * per_year), 4),
        excess_net_ann=round(float((np.mean(tops) - COST_RT - np.mean(alls)) * per_year), 4))

def verdict(m):
    if not m.get("days"): return "no output"
    return "PREDICTS" if (m["ic_tstat"] > 2 and m["excess_net_ann"] > 0) else "no proven edge"
