"""vD4 = ridge, walk-forward (labels known before Y-01-01), on cross-sectionally rank-normalised features
[vol5, vol21, vol63, park21, ewabs, gap5, vsurge, beta*vix] ; label = cross-sectional rank of realised |5d return|."""
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from lab import long as L
from skills_long.vD_feat import build, rank_by_date
COLS = ["vol5", "vol21", "vol63", "park21", "ewabs", "gap5", "vsurge", "beta"]
def prep(panel, market, cols):
    X = build(panel, market); R = rank_by_date(X, cols); R.columns = ["r_" + c for c in cols]
    # beta x market-vol interaction on rank scale (VIX scaled to ~1 at 20)
    R["r_betavix"] = R["r_beta"] * (X.mktvol.values * 5 - 1) if "r_beta" in R else 0
    R = R.fillna(0).astype("float32")
    X = pd.concat([X[["symbol", "date"]], R], axis=1)
    T = L.targets(panel, "abs"); T["y"] = T.groupby("date").target.rank(pct=True) - 0.5
    X = X.merge(T[["symbol", "date", "y", "target_end"]], on=["symbol", "date"], how="left")
    return X, [c for c in X.columns if c.startswith("r_")]
def fit_fn(Xt, yt): return Ridge(alpha=10.0).fit(Xt, yt)
def predict_abs(panel, market):
    X, fc = prep(panel, market, COLS)
    first, last = int(X.date.min()[:4]) , int(X.date.max()[:4])
    # train subsample: every 5th date to cut cost (label overlap is 5d anyway)
    keep = X.date.map(lambda d: True)
    ud = np.sort(X.date.unique()); sub = set(ud[::5])
    Xs = X.copy(); Xs["y"] = np.where(X.date.isin(sub), X.y, np.nan)
    pred = L.walk_forward(Xs, fc, "y", "target_end", fit_fn, first, last)
    out = X[["symbol", "date"]].assign(score=pred.values)
    return out.dropna()
