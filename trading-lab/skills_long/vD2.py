"""vD2 = equal-weight average of cross-sectional ranks of vol5, vol21, vol63. No fitting."""
from skills_long.vD_feat import build, rank_by_date
def predict_abs(panel, market):
    X = build(panel, market); c = ["vol5", "vol21", "vol63"]; r = rank_by_date(X, c)
    return X[["symbol", "date"]].assign(score=r.mean(axis=1).values).dropna()
