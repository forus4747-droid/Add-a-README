"""vB core: walk-forward ML ranker on price/volume + market-regime features (no size/liquidity-level features).
cfg keys: model ('ridge'|'lgbm'), window (None=expanding, or years), regime (bool), refit ('year'), step (train every k-th day)."""
import numpy as np, pandas as pd

BASE = ["ret1","ret2","ret3","ret5","ret10","ret21","ret63","ret126","mom_12_1","vol5","vol21","vol63","vol_ratio","park21","gap","intraday",
        "ovn21","intra21","clv","clv5","dist_high21","dist_high252","dist_low252","ma20","ma50","ma200","rsi14","bb_pos","rel_vol5","rel_vol1",
        "retxvol5","beta63","res5","res21","idio63","maxret21","minret21","skew63","ret5_vs","ret1_vs"]
REG = ["vix","vix_chg5","mkt21","mkt5","trend200","term"]
INTER = ["ret1","ret2","ret5","ret21","vol21","vol_ratio","clv","dist_high252","beta63","res5"]  # features interacted with regime (ridge)

def _wide(panel, col, dates, syms, di, si):
    a = np.full((len(dates), len(syms)), np.nan, np.float32); a[di, si] = panel[col].values; return pd.DataFrame(a, index=dates, columns=syms)

def features(panel, market):
    dates = np.array(sorted(panel.date.unique())); syms = np.array(sorted(panel.symbol.unique()))
    di = np.searchsorted(dates, panel.date.values); si = np.searchsorted(syms, panel.symbol.values)
    W = {c: _wide(panel, c, dates, syms, di, si) for c in ["open","high","low","close","volume"]}
    univ = np.zeros((len(dates), len(syms)), bool); univ[di, si] = panel.in_univ.values
    c, o, h, l, v = W["close"], W["open"], W["high"], W["low"], W["volume"]
    mk = market.reindex(dates); spx = (mk["SPY"] if "SPY" in mk else mk["_GSPC"]).astype(np.float32)
    mret = spx.pct_change(); mret = mret.fillna(0)
    r1 = c.pct_change(fill_method=None); F = {}
    for n in (1,2,3,5,10,21,63,126): F[f"ret{n}"] = c / c.shift(n) - 1
    F["mom_12_1"] = c.shift(21) / c.shift(252) - 1
    def rl(x, n, f, mp=None): return getattr(x.rolling(n, min_periods=mp or max(5, n // 2)), f)().astype(np.float32)
    for n in (5,21,63): F[f"vol{n}"] = rl(r1, n, "std")
    F["vol_ratio"] = F["vol5"] / F["vol63"]
    F["ret5_vs"] = F["ret5"] / F["vol63"].clip(lower=0.003); F["ret1_vs"] = F["ret1"] / F["vol63"].clip(lower=0.003)
    F["park21"] = np.sqrt(rl(np.log(h / l) ** 2, 21, "mean"))
    pc = c.shift(1); F["gap"] = o / pc - 1; F["intraday"] = c / o - 1
    F["ovn21"] = rl(o / pc - 1, 21, "sum"); F["intra21"] = rl(c / o - 1, 21, "sum")
    clv = (c - l) / (h - l).replace(0, np.nan); F["clv"] = clv; F["clv5"] = rl(clv, 5, "mean")
    F["dist_high21"] = c / rl(h, 21, "max") - 1; F["dist_high252"] = c / rl(h, 252, "max", 126) - 1; F["dist_low252"] = c / rl(l, 252, "min", 126) - 1
    for n in (20,50,200): F[f"ma{n}"] = c / rl(c, n, "mean") - 1
    up = (c - pc).clip(lower=0); dn = (pc - c).clip(lower=0); F["rsi14"] = rl(up, 14, "mean") / (rl(up, 14, "mean") + rl(dn, 14, "mean"))
    F["bb_pos"] = (c - rl(c, 20, "mean")) / rl(c, 20, "std")
    F["rel_vol5"] = rl(v, 5, "mean") / rl(v, 63, "mean"); F["rel_vol1"] = v / rl(v, 21, "mean")
    F["retxvol5"] = rl(r1 * np.sign(v / v.shift(1) - 1), 5, "sum")
    m = mret.astype(np.float32).values[:, None]; mx, my = rl(pd.DataFrame(np.repeat(m, len(syms), 1), index=dates, columns=syms), 63, "mean"), rl(r1, 63, "mean")
    mm = pd.DataFrame(np.repeat(m, len(syms), 1), index=dates, columns=syms)
    beta = (rl(r1 * mm, 63, "mean") - mx * my) / (rl(mm * mm, 63, "mean") - mx * mx).clip(lower=1e-8); F["beta63"] = beta
    res = r1 - beta.shift(1) * mm; F["res5"] = rl(res, 5, "sum"); F["res21"] = rl(res, 21, "sum"); F["idio63"] = rl(res, 63, "std")
    F["maxret21"] = rl(r1, 21, "max"); F["minret21"] = rl(r1, 21, "min"); F["skew63"] = rl(r1, 63, "skew")
    F = {k: x.astype(np.float32) for k, x in F.items()}
    U = np.where(univ, 1.0, np.nan).astype(np.float32)
    nrow = int(univ.sum()); X = np.empty((nrow, len(BASE)), np.float32)
    for j, k in enumerate(BASE):
        f = F[k].values.astype(np.float32); f[~np.isfinite(f)] = np.nan
        rk = pd.DataFrame(f * U).rank(axis=1, pct=True).values.astype(np.float32) - 0.5
        X[:, j] = np.nan_to_num(rk[univ], nan=0.0); del rk, f
    ii, jj = np.nonzero(univ)
    # regime variables (market series only, by date)
    vix = mk["_VIX"].astype(np.float32); tnx, irx = mk["_TNX"], mk["_IRX"]
    R = pd.DataFrame({"vix": (vix - 20) / 10, "vix_chg5": (vix / vix.shift(5) - 1) * 3, "mkt21": (spx.pct_change(21) / 0.05).clip(-3, 3),
                      "mkt5": (spx.pct_change(5) / 0.025).clip(-3, 3), "trend200": (spx / spx.rolling(200, min_periods=100).mean() - 1) / 0.05,
                      "term": (tnx - irx) / 2}).clip(-4, 4).fillna(0).astype(np.float32)
    # label: fwd 5d o2o return, demeaned per day, / trailing vol, ranked
    fwd = (o.shift(-6) / o.shift(-1) - 1).clip(-0.5, 0.5)
    z = fwd.sub(fwd.where(univ).mean(axis=1), axis=0) / F["vol63"].clip(lower=0.005)
    lab = (pd.DataFrame(z.values * U).rank(axis=1, pct=True).values - 0.5).astype(np.float32)[univ]
    dend = np.append(dates[6:], [None] * 6)  # date[t+6] when label becomes known
    meta = pd.DataFrame({"symbol": syms[jj], "date": dates[ii], "label": lab, "label_end": dend[ii]})
    meta.loc[meta.label_end.isna(), "label"] = np.nan; meta["label_end"] = meta.label_end.fillna("9999-12-31")
    return meta, X, R.values[ii], np.array(R.columns)

def _design(X, Rv, regime, model):
    if not regime: return X
    if model == "lgbm": return np.hstack([X, Rv])
    ix = [BASE.index(k) for k in INTER]
    inter = np.hstack([X[:, ix] * Rv[:, [r]] for r in range(Rv.shape[1])])
    return np.hstack([X, Rv, inter])

def fit_model(model, Xtr, ytr, seed=0):
    if model == "ridge":
        from sklearn.linear_model import Ridge
        return Ridge(alpha=3000.0, fit_intercept=True).fit(Xtr, ytr)
    import lightgbm as lgb
    return lgb.LGBMRegressor(n_estimators=150, learning_rate=0.05, num_leaves=15, max_depth=4, min_child_samples=2000, subsample=0.5, subsample_freq=1,
                             colsample_bytree=0.6, reg_lambda=50.0, max_bin=63, n_jobs=2, random_state=seed, deterministic=True, force_row_wise=True, verbose=-1).fit(Xtr, ytr)

def v0_score(panel):
    p = panel.sort_values(["symbol", "date"]); g = p.groupby("symbol", sort=False).close
    f = pd.DataFrame({"symbol": p.symbol, "date": p.date, "r1": p.close / g.shift(1) - 1, "r2": p.close / g.shift(2) - 1, "r5": p.close / g.shift(5) - 1})[p.in_univ.values]
    r = f.groupby("date")[["r1", "r2", "r5"]].rank(pct=True) - 0.5
    return f[["symbol", "date"]].assign(score=(-r.mean(axis=1)).values).dropna()

def predict_cfg(panel, market, cfg):
    model, window, regime, step, min_years = cfg["model"], cfg.get("window"), cfg.get("regime", False), cfg.get("step", 2), cfg.get("min_years", 3)
    meta, X, Rv, _ = features(panel, market)
    D = _design(X, Rv, regime, model); del X
    yr = meta.date.str[:4].astype(int).values; lab = meta.label.values; lend = meta.label_end.values
    didx = pd.factorize(meta.date.values, sort=True)[0]
    score = np.full(len(meta), np.nan, np.float32); done = np.zeros(len(meta), bool)
    for Y in range(1991, int(yr.max()) + 1):
        te = yr == Y
        if not te.any(): continue
        tr = (lend < f"{Y}-01-01") & ~np.isnan(lab) & (didx % step == 0)
        if window: tr &= yr >= Y - window
        if len(np.unique(yr[tr])) < min_years: continue
        m = fit_model(model, D[tr], lab[tr]); score[te] = m.predict(D[te]); done[te] = True
    out = meta[["symbol", "date"]].assign(score=score)
    if not done.all():  # early years with too little history to fit: fall back to v0's fixed formula
        base = v0_score(panel).rename(columns={"score": "s0"}); out = out.merge(base, on=["symbol", "date"], how="left")
        out["score"] = np.where(done[np.arange(len(out))], out.score, out.s0); out = out.drop(columns="s0")
    return out.dropna(subset=["score"])
