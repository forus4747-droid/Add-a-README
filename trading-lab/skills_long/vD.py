"""vD = equal-weight rank average of vol21, vol63, Parkinson21, EWMA|r|. No fitting."""
from skills_long.vD_feat import build, rank_by_date
def predict_abs(panel, market):
    X = build(panel, market); c = ["vol21", "vol63", "park21", "ewabs"]; r = rank_by_date(X, c)
    return X[["symbol", "date"]].assign(score=r.mean(axis=1).values).dropna()
