"""vD5 = LightGBM (n_jobs=2, seed 0), walk-forward, same rank features + raw VIX level + raw log vol21; label rank|ret|."""
import numpy as np, pandas as pd, lightgbm as lgb
from lab import long as L
from skills_long.vD_feat import build, rank_by_date
COLS = ["vol5", "vol21", "vol63", "park21", "ewabs", "gap5", "gap21", "vsurge", "beta", "ldv", "absr1"]
def fit_fn(Xt, yt):
    return lgb.LGBMRegressor(n_estimators=150, learning_rate=0.05, num_leaves=15, min_child_samples=2000, subsample=0.5, subsample_freq=1,
                             colsample_bytree=0.8, reg_lambda=10, n_jobs=2, random_state=0, verbose=-1).fit(Xt, yt)
def predict_abs(panel, market):
    X = build(panel, market); R = rank_by_date(X, COLS); R.columns = ["r_" + c for c in COLS]
    R["mktvol"] = X.mktvol.values; R["lvol21"] = np.log(X.vol21.values + 1e-4)
    R = R.astype("float32"); fc = list(R.columns)
    X = pd.concat([X[["symbol", "date"]], R], axis=1)
    T = L.targets(panel, "abs"); T["y"] = T.groupby("date").target.rank(pct=True) - 0.5
    X = X.merge(T[["symbol", "date", "y", "target_end"]], on=["symbol", "date"], how="left")
    ud = np.sort(X.date.unique()); sub = set(ud[::5]); Xs = X.copy(); Xs["y"] = np.where(X.date.isin(sub), X.y, np.nan)
    pred = L.walk_forward(Xs, fc, "y", "target_end", fit_fn, int(ud[0][:4]), int(ud[-1][:4]))
    return X[["symbol", "date"]].assign(score=pred.values).dropna()
