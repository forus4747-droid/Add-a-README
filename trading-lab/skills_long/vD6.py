"""vD6 = vD4 ridge (walk-forward) with fixed fallback for years without >=5 years of known labels:
fallback = equal-weight rank average of vol21, vol63, park21, ewabs (= vD3). Full 1991-2012 coverage."""
import numpy as np, pandas as pd
from skills_long import vD4
from skills_long.vD_feat import build, rank_by_date
def predict_abs(panel, market):
    X, fc = vD4.prep(panel, market, vD4.COLS)
    ud = np.sort(X.date.unique()); sub = set(ud[::5]); Xs = X.copy(); Xs["y"] = np.where(X.date.isin(sub), X.y, np.nan)
    from lab import long as L
    pred = L.walk_forward(Xs, fc, "y", "target_end", vD4.fit_fn, int(ud[0][:4]), int(ud[-1][:4]))
    fb = X[["r_vol21", "r_vol63", "r_park21", "r_ewabs"]].mean(axis=1)   # ranks already per-date, centred
    s = pred.where(pred.notna(), fb)
    return X[["symbol", "date"]].assign(score=s.values).dropna()
