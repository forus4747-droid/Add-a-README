"""ML4T (stefan-jansen/machine-learning-for-trading) price/volume factors -> results/preds/ml4t_<factor>_swing.parquet
plus a combined LightGBM model ml4t_gbm. Usage (from trading-lab): PY skills/ml4t/run.py
Sources: see FACTORS (file:line) and reports/notes/ml4t.md. Everything is causal: per-symbol rolling windows on rows <= t.
Steps: 1) factors on full history (2016-2025)  2) write 12 factor preds (2024-01-01..2025-12-31)
       3) GBM fit on TRAIN/early-stop 2023, predict 2024-25, ONE run  4) truncation test (3 pairs per family)."""
import sys, os, json, warnings
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, ROOT)
import numpy as np, pandas as pd, talib, lightgbm as lgb
from numpy.lib.stride_tricks import sliding_window_view
from lab.data import load_daily

LO, HI = "2024-01-01", "2025-12-31"
SEED = 42
P08 = "08_financial_features/01_price_volume_features.py"
CS3 = "case_studies/us_equities_panel/03_financial_features.py"

# name: (family, direction(+1 higher=better,-1 lower=better), source citation)
FACTORS = {
 "mom_skip1_21d":  ("momentum", +1, f"{P08}:228"),
 "mom_12_1":       ("momentum", +1, f"{CS3}:341-370"),
 "volscaled_mom21": ("momentum", +1, f"{P08}:1186-1196"),
 "reversal_1d":    ("reversal", +1, f"{P08}:453"),          # score = -ret_1d (repo's own definition)
 "reversal_5d":    ("reversal", -1, f"{CS3}:587,620"),      # ret_5d; repo uses (1-rank(ret_5d)) as contrarian => lower better
 "ma_dist_atr21":  ("trend", +1, f"{P08}:286-310"),
 "slope21":        ("trend", +1, f"{P08}:406-436"),
 "vwap_dist5":     ("trend", +1, f"{P08}:1079-1118"),
 "vol_parkinson21": ("volatility", +1, f"{P08}:582-586"),    # no direction stated -> raw
 "vol_ratio_10_63": ("volatility", +1, f"{P08}:858-873"),    # no direction stated -> raw
 "rel_volume21":   ("volume", +1, f"{P08}:968-977"),         # no direction stated -> raw
 "amihud21":       ("liquidity", +1, f"{CS3}:491-505,556-566"),  # "illiquidity positively predicts returns" => higher better
}
STATED = {"vol_parkinson21": "raw (no direction stated)", "vol_ratio_10_63": "raw (no direction stated)",
          "rel_volume21": "raw (no direction stated)"}

def _g(df, col): return df.groupby("symbol", sort=False)[col]

def wilder_atr(g, n):
    return pd.Series(talib.ATR(g.high.values, g.low.values, g.close.values, timeperiod=n), index=g.index)

def reg_slope(g, n=21):
    """repo: polyfit slope over window / window mean * n (rolling_regression_slope)."""
    c = g.close.values.astype(float); out = np.full(len(c), np.nan)
    if len(c) >= n:
        W = sliding_window_view(c, n); x = np.arange(n) - (n - 1) / 2
        slope = (W * x).sum(1) / (x ** 2).sum()
        out[n - 1:] = slope / W.mean(1) * n
    return pd.Series(out, index=g.index)

def compute(df, names):
    """df sorted by symbol,date with open/high/low/close/volume. Returns DataFrame of RAW factor values (before sign)."""
    out = pd.DataFrame(index=df.index); c = df.close; gc = _g(df, "close")
    ret1 = gc.pct_change(1)
    need = set(names)
    if "mom_skip1_21d" in need: out["mom_skip1_21d"] = gc.shift(1) / gc.shift(21) - 1
    if "mom_12_1" in need: out["mom_12_1"] = gc.shift(21) / gc.shift(252) - 1
    if "volscaled_mom21" in need:
        vol21 = ret1.groupby(df.symbol, sort=False).rolling(21).std().reset_index(level=0, drop=True) * np.sqrt(252)
        out["volscaled_mom21"] = gc.pct_change(21) / vol21.clip(lower=1e-10)
    if "reversal_1d" in need: out["reversal_1d"] = -ret1
    if "reversal_5d" in need: out["reversal_5d"] = gc.pct_change(5)
    if "ma_dist_atr21" in need:
        sma = gc.rolling(21).mean().reset_index(level=0, drop=True) if False else c.groupby(df.symbol, sort=False).transform(lambda s: s.rolling(21).mean())
        atr = pd.concat([wilder_atr(g, 21) for _, g in df.groupby("symbol", sort=False)])
        out["ma_dist_atr21"] = (c - sma) / atr.reindex(df.index).clip(lower=1e-10)
    if "slope21" in need: out["slope21"] = pd.concat([reg_slope(g) for _, g in df.groupby("symbol", sort=False)]).reindex(df.index)
    if "vwap_dist5" in need:
        tp = (df.high + df.low + df.close) / 3; tv = tp * df.volume
        num = tv.groupby(df.symbol, sort=False).transform(lambda s: s.rolling(5).sum())
        den = df.volume.groupby(df.symbol, sort=False).transform(lambda s: s.rolling(5).sum())
        out["vwap_dist5"] = c / (num / den) - 1
    if "vol_parkinson21" in need:
        x = (np.log(df.high) - np.log(df.low)) ** 2 / (4 * np.log(2))
        out["vol_parkinson21"] = np.sqrt(x.groupby(df.symbol, sort=False).transform(lambda s: s.rolling(21).mean()) * 252)
    if "vol_ratio_10_63" in need:
        lr = np.log(c).groupby(df.symbol, sort=False).diff()
        s10 = lr.groupby(df.symbol, sort=False).transform(lambda s: s.rolling(10).std()) * np.sqrt(252)
        s63 = lr.groupby(df.symbol, sort=False).transform(lambda s: s.rolling(63).std()) * np.sqrt(252)
        out["vol_ratio_10_63"] = s10 / s63.clip(lower=1e-10)
    if "rel_volume21" in need:
        out["rel_volume21"] = df.volume / df.volume.groupby(df.symbol, sort=False).transform(lambda s: s.rolling(21).mean())
    if "amihud21" in need:
        dv = df.close * df.volume
        a = ret1.abs() / (dv + 1)
        out["amihud21"] = a.groupby(df.symbol, sort=False).transform(lambda s: s.rolling(21).mean())
    return out[[n for n in names]].replace([np.inf, -np.inf], np.nan)

def signed(raw):
    s = raw.copy()
    for n in s.columns:
        if n == "reversal_1d": continue            # factor already defined as -ret_1d
        s[n] = FACTORS[n][1] * s[n]
    return s

def rank_norm(F, dates):
    """per-day cross-sectional rank in (-0.5,0.5); NaN stays NaN. Only uses same-day cross-section."""
    return F.groupby(dates.values).rank(pct=True) - 0.5

def main():
    d = load_daily(stocks_only=True).sort_values(["symbol", "date"]).reset_index(drop=True)
    names = list(FACTORS)
    raw = compute(d, names); S = signed(raw)
    os.makedirs("results/preds", exist_ok=True)
    m = (d.date >= LO) & (d.date <= HI)
    for n in names:
        p = pd.DataFrame({"symbol": d.symbol, "date": d.date, "score": S[n]})[m].dropna()
        p.to_parquet(f"results/preds/ml4t_{n}_swing.parquet", index=False)
        print(n, len(p))

    # ---------- combined GBM ----------
    g = d.groupby("symbol", sort=False)
    d["label"] = (g.open.shift(-6) / g.open.shift(-1) - 1).clip(-0.5, 0.5)
    d["label_end"] = g.date.shift(-6)
    X = rank_norm(S, d.date)           # signed vs raw irrelevant for trees; rank-normalised per day
    ok = X.notna().all(1) & d.label.notna()
    tr = ok & (d.date <= "2022-12-31") & (d.label_end <= "2022-12-31")      # labels end inside TRAIN-fit window
    va = ok & (d.date >= "2023-01-01") & (d.date <= "2023-12-31") & (d.label_end <= "2023-12-31")
    assert d.loc[tr, "label_end"].max() <= "2022-12-31" and d.loc[va, "label_end"].max() <= "2023-12-31"
    print("train rows", tr.sum(), "valid rows", va.sum())
    params = dict(objective="regression", seed=SEED, verbose=-1, num_threads=8, deterministic=True, force_row_wise=True)
    # repo default_mse preset (case_studies/config/lgb/default_mse.yaml): objective=regression, seed=42, max_iterations=500,
    # everything else = LightGBM defaults (learning_rate 0.1, num_leaves 31)
    dtr = lgb.Dataset(X[tr].values, d.label[tr].values); dva = lgb.Dataset(X[va].values, d.label[va].values, reference=dtr)
    bst = lgb.train(params, dtr, num_boost_round=500, valid_sets=[dva],
                    callbacks=[lgb.early_stopping(50, verbose=False)])
    print("best_iteration", bst.best_iteration)
    pr = (d.date >= LO) & (d.date <= HI) & X.notna().all(1)
    p = pd.DataFrame({"symbol": d.symbol[pr], "date": d.date[pr],
                      "score": bst.predict(X[pr].values, num_iteration=bst.best_iteration)})
    p.to_parquet("results/preds/ml4t_gbm_swing.parquet", index=False)
    print("gbm preds", len(p))
    imp = dict(zip(names, bst.feature_importance("gain").round(0)))
    json.dump(dict(best_iteration=int(bst.best_iteration), train_rows=int(tr.sum()), valid_rows=int(va.sum()),
                   gain_importance=imp), open("results/ml4t_gbm_info.json", "w"), indent=1)

    # ---------- truncation test ----------
    rng = np.random.default_rng(7)
    fams = {}
    for n, (f, _, _) in FACTORS.items(): fams.setdefault(f, []).append(n)
    pool = d[(d.date >= LO) & (d.date <= HI)][["symbol", "date"]]
    rows = []; allok = True
    for fam, ns in fams.items():
        for i in rng.choice(len(pool), 3, replace=False):
            sym, dt = pool.iloc[i]
            cut = d[d.date <= dt][["symbol", "date", "open", "high", "low", "close", "volume"]].reset_index(drop=True)
            Sc = signed(compute(cut, ns))
            ci = cut.index[(cut.symbol == sym) & (cut.date == dt)][0]; fi = d.index[(d.symbol == sym) & (d.date == dt)][0]
            a, b = Sc.loc[ci, ns].values.astype(float), S.loc[fi, ns].values.astype(float)
            ok_ = bool(np.allclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True)); allok &= ok_
            rows.append(dict(family=fam, symbol=sym, date=dt, ok=ok_, max_abs_diff=float(np.nanmax(np.abs(a - b))) if not np.isnan(a).all() else 0.0))
    # GBM: features cut at date -> same-day rank -> same trained model -> same score
    for i in rng.choice(len(p), 3, replace=False):
        sym, dt = p.iloc[i].symbol, p.iloc[i].date
        cut = d[d.date <= dt][["symbol", "date", "open", "high", "low", "close", "volume"]].reset_index(drop=True)
        Xc = rank_norm(signed(compute(cut, names)), cut.date)
        ci = cut.index[(cut.symbol == sym) & (cut.date == dt)][0]
        sc = bst.predict(Xc.loc[[ci]].values, num_iteration=bst.best_iteration)[0]
        ok_ = bool(abs(sc - p.iloc[i].score) < 1e-12); allok &= ok_
        rows.append(dict(family="gbm", symbol=sym, date=dt, ok=ok_, max_abs_diff=float(abs(sc - p.iloc[i].score))))
    t = pd.DataFrame(rows); print(t.to_string(index=False)); t.to_csv("results/ml4t_truncation_test.csv", index=False)
    print("TRUNCATION TEST", "PASS" if allok else "FAIL")

if __name__ == "__main__":
    main()
