"""Phase 2 harness (PROTOCOL_V3_LONG). Workers' data root ends 2012-12-31; nothing later exists there."""
import os, numpy as np, pandas as pd
ROOT = os.environ.get("LAB_LONG", "/home/user/trading-stack/data_loop")
COST_RT = 0.001; H = 5

def load_panel():
    """symbol,date,open,high,low,close,volume,dollar_vol,raw_close,in_univ  (prices split+dividend adjusted)"""
    return pd.read_parquet(f"{ROOT}/panel.parquet")

def load_market():
    """wide DataFrame indexed by date: adjusted closes of SPY, QQQ, IWM, sector ETFs, _GSPC, _VIX, _TNX, _IRX (NaN before inception)"""
    return pd.read_parquet(f"{ROOT}/market.parquet")

def targets(panel, kind="return"):
    """(symbol,date,target,target_end) for in-universe rows. target = open[t+6]/open[t+1]-1 ; kind='abs' -> |target|"""
    p = panel.sort_values(["symbol", "date"]); g = p.groupby("symbol", sort=False)
    t = g.open.shift(-6) / g.open.shift(-1) - 1
    out = pd.DataFrame({"symbol": p.symbol, "date": p.date, "target": t.abs() if kind == "abs" else t, "target_end": g.date.shift(-6), "in_univ": p.in_univ})
    return out[out.in_univ].drop(columns="in_univ").dropna()

def _daily(preds, T, lo, hi):
    t = T[(T.date >= lo) & (T.target_end <= hi)]; x = t.merge(preds[["symbol", "date", "score"]], on=["symbol", "date"], how="inner").dropna()
    rows = []
    for dt, g in x.groupby("date"):
        if len(g) < 100 or g.score.nunique() < 10: continue
        r = g.score.rank(pct=True); q5, q1 = g.target[r > 0.8].mean(), g.target[r <= 0.2].mean()
        rows.append((dt, g.score.rank().corr(g.target.rank()), ((g.score > g.score.median()) == (g.target > g.target.median())).mean(), q5, q1, g.target.mean(), len(g)))
    return pd.DataFrame(rows, columns=["date", "ic", "hit", "top", "bot", "all", "n"]), len(x) / max(len(t), 1)

def score(preds, T, lo, hi):
    """Per-year table + pooled summary dict for the window [lo, hi]."""
    d, cov = _daily(preds, T, lo, hi)
    if d.empty: return pd.DataFrame(), dict(days=0)
    d["year"] = d.date.str[:4]; k = 252 / H
    y = d.groupby("year").agg(days=("ic", "size"), rank_ic=("ic", "mean"), hit_rate=("hit", "mean"), spread=("top", "mean"), bot=("bot", "mean"), ew=("all", "mean"))
    y["top_minus_bottom"] = y.spread - y.bot; y["top_q_net_ann"] = (y.spread - COST_RT) * k; y["excess_net_ann"] = (y.spread - COST_RT - y.ew) * k
    y = y.drop(columns=["spread", "bot", "ew"]).round(5)
    s = dict(days=len(d), coverage=round(cov, 3), years=len(y), mean_yearly_ic=round(float(y.rank_ic.mean()), 5), years_positive=int((y.rank_ic > 0).sum()),
             share_years_positive=round(float((y.rank_ic > 0).mean()), 3), pooled_tstat=round(float(d.ic.mean() / d.ic.std(ddof=1) * np.sqrt(len(d) / H)), 2),
             hit_rate=round(float(d.hit.mean()), 4), top_minus_bottom=round(float((d.top - d.bot).mean()), 5),
             excess_net_ann=round(float((d.top.mean() - COST_RT - d["all"].mean()) * k), 4))
    s["verdict"] = "PREDICTS" if (s["pooled_tstat"] > 3 and s["share_years_positive"] >= 0.75 and s["excess_net_ann"] > 0) else "no proven edge"
    return y, s

def diagnose(preds, panel, market, lo, hi, kind="return"):
    """Where is a version right or wrong? Rank IC split by regime/segment. Returns dict of small DataFrames."""
    T = targets(panel, kind); x = T[(T.date >= lo) & (T.target_end <= hi)].merge(preds[["symbol", "date", "score"]], on=["symbol", "date"]).dropna()
    p = panel.sort_values(["symbol", "date"]); g = p.groupby("symbol", sort=False)
    f = pd.DataFrame({"symbol": p.symbol, "date": p.date, "vol63": g.close.pct_change().groupby(p.symbol, sort=False).rolling(63, min_periods=30).std().reset_index(level=0, drop=True),
                      "dv63": g.dollar_vol.rolling(63, min_periods=30).median().reset_index(level=0, drop=True), "ret5": p.close / g.close.shift(5) - 1})
    x = x.merge(f, on=["symbol", "date"], how="left")
    m = market.copy(); sp = m["_GSPC"] if "_GSPC" in m else m["SPY"]
    reg = pd.DataFrame({"vix_level": pd.cut(m["_VIX"], [0, 15, 20, 30, 200], labels=["<15", "15-20", "20-30", ">30"]),
                        "mkt_21d": pd.cut(sp.pct_change(21), [-1, -0.05, 0, 0.05, 1], labels=["<-5%", "-5..0", "0..5", ">5%"]),
                        "mkt_above_200d": np.where(sp > sp.rolling(200).mean(), "above", "below")}, index=m.index)
    x = x.merge(reg, left_on="date", right_index=True, how="left"); x["weekday"] = pd.to_datetime(x.date).dt.day_name().str[:3]
    def ic_by(col, xs=False):
        if xs:  # cross-sectional bucket within each day
            x["_b"] = x.groupby("date")[col].transform(lambda s: pd.qcut(s.rank(method="first"), 3, labels=["low", "mid", "high"]))
            col = "_b"
        r = x.groupby([col, "date"], observed=True).apply(lambda g: g.score.rank().corr(g.target.rank()) if len(g) >= 30 else np.nan).dropna()
        return r.groupby(level=0, observed=True).agg(mean_ic="mean", days="size", tstat=lambda s: s.mean() / s.std(ddof=1) * np.sqrt(len(s) / H)).round(4)
    out = {"by_vix": ic_by("vix_level"), "by_market_21d": ic_by("mkt_21d"), "by_trend": ic_by("mkt_above_200d"), "by_weekday": ic_by("weekday"),
           "by_stock_volatility": ic_by("vol63", True), "by_stock_liquidity": ic_by("dv63", True), "by_stock_recent_5d_move": ic_by("ret5", True)}
    x["dec"] = x.groupby("date").score.transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=False))
    out["by_score_decile_mean_target_pct"] = (x.groupby("dec").target.mean() * 100).round(4).to_frame("mean_target_pct")
    return out

def check_causal(predict_fn, panel, market, n=3, seed=0, tol=1e-9):
    """Truncation test: scores for a date must not change when all later rows are removed."""
    full = predict_fn(panel, market); rng = np.random.default_rng(seed); dates = sorted(full.date.unique()); res = []
    for dt in rng.choice(dates[len(dates) // 3:], n, replace=False):
        t = predict_fn(panel[panel.date <= dt], market[market.index <= dt]); t = t[t.date == dt].merge(full[full.date == dt], on=["symbol", "date"])
        res.append(dict(date=dt, rows=len(t), max_abs_diff=float((t.score_x - t.score_y).abs().max()) if len(t) else None))
    ok = all(r["rows"] > 0 and r["max_abs_diff"] <= tol for r in res)
    return ok, res

def walk_forward(X, cols, label_col, label_end_col, fit_fn, first_year, last_year, min_years=5):
    """Honest fitting helper. For each year Y: fit_fn(Xtrain, ytrain) -> model with .predict, using only rows whose
    label was known before Y-01-01; predict rows dated in Y. Returns Series of predictions aligned to X.index (NaN before first_year)."""
    out = pd.Series(np.nan, index=X.index); yr = X.date.str[:4].astype(int)
    for Y in range(first_year, last_year + 1):
        tr = X[(X[label_end_col] < f"{Y}-01-01") & X[label_col].notna()]; te = X[yr == Y]
        if len(te) == 0 or tr.date.str[:4].nunique() < min_years: continue
        out.loc[te.index] = fit_fn(tr[cols].values, tr[label_col].values).predict(te[cols].values)
    return out
