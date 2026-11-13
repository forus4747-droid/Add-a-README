"""Shared causal feature builder for the vD risk versions. Every feature at (symbol, t) uses rows dated <= t only.
Memory-lean: wide float32 matrices, features extracted for in-universe cells immediately."""
import gc, numpy as np, pandas as pd

def build(panel, market):
    p = panel[["symbol", "date", "open", "high", "low", "close", "volume", "dollar_vol", "in_univ"]]
    W = lambda c: p.pivot(index="date", columns="symbol", values=c).sort_index().astype("float32")
    mask = p.pivot(index="date", columns="symbol", values="in_univ").sort_index().fillna(False).values.astype(bool)
    ri, ci = np.nonzero(mask)
    out = {}
    def put(name, wide):
        out[name] = wide.values[ri, ci].astype("float32")
    close = W("close"); idx, cols = close.index, close.columns
    r = close.pct_change(fill_method=None)
    for w in (5, 21, 63): put(f"vol{w}", r.rolling(w, min_periods=max(4, int(w * .7))).std())
    put("ewabs", r.abs().ewm(halflife=10, min_periods=15).mean()); put("absr1", r.abs())
    mk = market["_GSPC"].reindex(idx).pct_change(fill_method=None).astype("float32")
    mv = mk.rolling(63, min_periods=40).var()
    cov = r.mul(mk, axis=0).rolling(63, min_periods=40).mean() - r.rolling(63, min_periods=40).mean().mul(mk.rolling(63, min_periods=40).mean(), axis=0)
    beta = cov.div(mv, axis=0).abs(); del cov, r; gc.collect()
    put("beta", beta); del beta
    hi, lo = W("high"), W("low")
    hl = np.log(hi / lo.where(lo > 0)) ** 2; del hi, lo
    put("park21", np.sqrt(hl.rolling(21, min_periods=15).mean() / (4 * np.log(2)))); del hl; gc.collect()
    op = W("open"); gap = (op / close.shift(1) - 1).abs(); del op, close; gc.collect()
    put("gap5", gap.rolling(5, min_periods=3).max()); put("gap21", gap.rolling(21, min_periods=15).max()); del gap
    vol = W("volume")
    put("vsurge", np.log((vol.rolling(5, min_periods=4).mean() + 1) / (vol.rolling(63, min_periods=40).mean() + 1))); del vol
    put("ldv", np.log(W("dollar_vol").rolling(21, min_periods=10).median() + 1)); gc.collect()
    vix = (market["_VIX"].reindex(idx).ffill().astype("float32").values / 100)
    X = pd.DataFrame(out); X.insert(0, "symbol", cols.values[ci]); X.insert(0, "date", idx.values[ri])
    X["mktvol"] = vix[ri]; X["beta_vix"] = X.beta * X.mktvol
    return X

def rank_by_date(X, cols):
    return X.groupby("date")[cols].rank(pct=True).astype("float32") - 0.5
