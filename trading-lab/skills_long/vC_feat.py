"""vC helpers: wide float32 (date x symbol) signal matrices. All signals use data <= t only."""
import numpy as np, pandas as pd

def wide(panel):
    p = panel[["symbol", "date", "open", "high", "low", "close", "volume", "in_univ"]]
    f = lambda c: p.pivot(index="date", columns="symbol", values=c).astype("float32")
    W = {c: f(c) for c in ["open", "close", "volume"]}
    W["univ"] = p.pivot(index="date", columns="symbol", values="in_univ").astype("boolean").fillna(False).astype(bool)
    return W

def xrank(df, mask):
    """cross-sectional pct rank - 0.5 among masked (in-universe) stocks each day; NaN elsewhere"""
    return df.where(mask).rank(axis=1, pct=True).astype("float32") - 0.5

def sigs(W):
    c, v, o, U = W["close"], W["volume"], W["open"], W["univ"]
    S = {}
    r1 = c / c.shift(1) - 1
    S["v0"] = -(xrank(c / c.shift(1) - 1, U) + xrank(c / c.shift(2) - 1, U) + xrank(c / c.shift(5) - 1, U)) / 3
    S["mom12_1"] = xrank(c.shift(21) / c.shift(252) - 1, U)
    S["hi52"] = xrank(c / c.rolling(252, min_periods=200).max(), U)
    S["lowvol"] = xrank(-r1.rolling(252, min_periods=200).std(), U)
    # event drift: gap on abnormally high volume; carry sign*(size) for 60 days
    gap = o / c.shift(1) - 1
    vr = v / v.rolling(63, min_periods=40).median().shift(1)
    sd = r1.rolling(63, min_periods=40).std().shift(1)
    ev = ((gap.abs() > 2 * sd) & (vr > 3)).astype("float32")
    evd = (np.sign(c / c.shift(1) - 1) * ev).fillna(0)  # direction of that day's close move
    S["event"] = xrank(evd.rolling(60, min_periods=1).sum().where(U), U)  # ties heavy; rank average handles
    return S


def daily_ic(s, t):
    m = s.notna() & t.notna()
    a = s.where(m).rank(axis=1); b = t.where(m).rank(axis=1)
    a = a.sub(a.mean(1), axis=0); b = b.sub(b.mean(1), axis=0)
    ic = (a * b).sum(1) / np.sqrt((a * a).sum(1) * (b * b).sum(1))
    return ic[m.sum(1) >= 100]

def wf_weights(S, W, names, min_years=3):
    """Per-year weights from expanding mean daily IC using only labels known before Y-01-01 (target ends at open[t+6])."""
    o = W["open"]; tgt = (o.shift(-6) / o.shift(-1) - 1).astype("float32")
    dates = list(S[names[0]].index); yrs = np.array([d[:4] for d in dates])
    ics = {k: daily_ic(S[k], tgt).reindex(dates) for k in names}
    out = {}
    for Y in sorted(set(yrs)):
        first = int(np.argmax(yrs == Y)); known = np.arange(len(dates)) + 6 < first  # label of day i ends at i+6
        if len(set(yrs[known])) < min_years: out[Y] = None; continue
        w = np.array([max(ics[k][known].mean(), 0.0) for k in names]); out[Y] = w / w.sum() if w.sum() > 0 else None
    return out

def combine_ew(S, names):
    return sum(S[k] for k in names) / len(names)

def combine_wf(S, W, names):
    wts = wf_weights(S, W, names); out = S["v0"].copy() * np.nan
    yrs = pd.Series(S["v0"].index.str[:4], index=S["v0"].index)
    for Y, w in wts.items():
        idx = yrs.index[yrs == Y]
        if w is None: out.loc[idx] = S["v0"].loc[idx]   # warm-up years: v0 only
        else: out.loc[idx] = sum(wi * S[k].loc[idx] for wi, k in zip(w, names))
    return out, wts
