"""Shared wide-matrix feature builder for vA variants. Only shifts/rolling over past data => causal."""
import numpy as np, pandas as pd

def wide(panel, col):
    return panel.pivot(index="date", columns="symbol", values=col).sort_index().astype("float32")

def build(panel, market):
    C, O, V = wide(panel, "close"), wide(panel, "open"), wide(panel, "volume")
    U = panel.pivot(index="date", columns="symbol", values="in_univ").reindex(index=C.index, columns=C.columns).fillna(False).astype(bool)
    W = {}
    W["r1"] = C / C.shift(1) - 1; W["r2"] = C / C.shift(2) - 1; W["r5"] = C / C.shift(5) - 1
    W["on1"] = O / C.shift(1) - 1; W["id1"] = C / O - 1
    r1 = W["r1"]
    W["vol"] = r1.rolling(63, min_periods=30).std()
    W["vr"] = V / V.rolling(63, min_periods=30).mean().shift(1)
    mk1 = r1.where(U).mean(axis=1)                       # equal-weight in-universe market return that day
    em = mk1.rolling(126, min_periods=60).mean(); emm = (mk1 * mk1).rolling(126, min_periods=60).mean()
    ex = r1.mul(mk1, axis=0).rolling(126, min_periods=60).mean(); er = r1.rolling(126, min_periods=60).mean()
    W["beta"] = (ex.sub(er.mul(em, axis=0))).div(emm - em * em, axis=0).clip(0, 3)
    lm = np.log1p(mk1)
    W["mkt1"] = pd.DataFrame(np.repeat(mk1.values[:, None], C.shape[1], 1), index=C.index, columns=C.columns).astype("float32")
    W["mkt2"] = pd.DataFrame(np.repeat(np.expm1(lm.rolling(2).sum()).values[:, None], C.shape[1], 1), index=C.index, columns=C.columns).astype("float32")
    W["mkt5"] = pd.DataFrame(np.repeat(np.expm1(lm.rolling(5).sum()).values[:, None], C.shape[1], 1), index=C.index, columns=C.columns).astype("float32")
    return {k: v.astype("float32") for k, v in W.items()}, U

def xrank(M, U):
    """cross-sectional pct rank - 0.5 among in-universe stocks each day (NaN elsewhere)"""
    return M.where(U).rank(axis=1, pct=True) - 0.5

def to_long(S, U):
    s = S.where(U).stack(dropna=True)
    s.index.names = ["date", "symbol"]
    return s.rename("score").reset_index()[["symbol", "date", "score"]]
