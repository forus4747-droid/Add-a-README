"""vD1 = baseline: trailing 21-day std of daily returns."""
from skills_long.vD_feat import build
def predict_abs(panel, market):
    X = build(panel, market); return X[["symbol", "date"]].assign(score=X.vol21.values).dropna()
