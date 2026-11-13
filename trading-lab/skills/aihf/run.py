"""ai-hedge-fund v1 rule-based technical signals -> results/preds/aihf_*_swing.parquet.
Vectorised per stock (every indicator is a causal rolling/ewm over the stock's own history), then verified against the
VERBATIM functions in technicals_v1.py on truncated data for N random (symbol, date) pairs (also the truncation test).
Usage: run.py [--n-check 300] [--seed 7]
"""
import sys, os, json, math, warnings, random
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import numpy as np, pandas as pd
import technicals_v1 as T
from lab.data import load_daily

LO, HI = "2024-01-01", "2025-12-31"
NAMES = {"trend": "aihf_trend", "mean_reversion": "aihf_meanrev", "momentum": "aihf_momentum",
         "volatility": "aihf_volatility", "stat_arb": "aihf_statarb"}
W = T.STRATEGY_WEIGHTS

def signed(sig, conf):
    """sig in {1,0,-1} array, conf array -> numeric score (+conf bullish, -conf bearish, 0 neutral)."""
    return np.where(sig == 1, conf, np.where(sig == -1, -conf, 0.0))

def vec_signals(df):
    """df: one stock, sorted by date, columns open/high/low/close/volume. Returns dict strategy -> (sig, conf) arrays
    where the value at row i equals what the verbatim function returns when given df.iloc[:i+1]."""
    c = df["close"]; n = len(df)
    # trend (T.calculate_trend_signals) -- reuse repo helpers on the full series (ewm is causal)
    d2 = df[["open", "high", "low", "close", "volume"]].copy()
    ema8, ema21, ema55 = T.calculate_ema(d2, 8), T.calculate_ema(d2, 21), T.calculate_ema(d2, 55)
    adx = T.calculate_adx(d2, 14)["adx"]
    st, mt = (ema8 > ema21).values, (ema21 > ema55).values
    ts = (adx / 100.0).values
    sig_tr = np.where(st & mt, 1, np.where(~st & ~mt, -1, 0)); conf_tr = np.where(sig_tr == 0, 0.5, ts)
    # mean reversion
    ma50 = c.rolling(50).mean(); sd50 = c.rolling(50).std(); z = ((c - ma50) / sd50).values
    bu, bl = T.calculate_bollinger_bands(d2); pbb = ((c - bl) / (bu - bl)).values
    b = (z < -2) & (pbb < 0.2); s = (z > 2) & (pbb > 0.8)
    sig_mr = np.where(b, 1, np.where(s, -1, 0)); conf_mr = np.where(sig_mr == 0, 0.5, np.minimum(np.abs(z) / 4, 1.0))
    # momentum
    r = c.pct_change()
    ms = (0.4 * r.rolling(21).sum() + 0.3 * r.rolling(63).sum() + 0.3 * r.rolling(126).sum()).values
    vc = (df["volume"] / df["volume"].rolling(21).mean()).values > 1.0
    b = (ms > 0.05) & vc; s = (ms < -0.05) & vc
    sig_mo = np.where(b, 1, np.where(s, -1, 0)); conf_mo = np.where(sig_mo == 0, 0.5, np.minimum(np.abs(ms) * 5, 1.0))
    # volatility
    hv = r.rolling(21).std() * math.sqrt(252); vma = hv.rolling(63).mean()
    reg = (hv / vma).values; vz = ((hv - vma) / hv.rolling(63).std()).values
    b = (reg < 0.8) & (vz < -1); s = (reg > 1.2) & (vz > 1)
    sig_vo = np.where(b, 1, np.where(s, -1, 0)); conf_vo = np.where(sig_vo == 0, 0.5, np.minimum(np.abs(vz) / 3, 1.0))
    # stat arb. Hurst: see notes -- in the repo code np.subtract(Series, Series) ALIGNS on the (date) index, so every
    # lagged difference is 0 -> tau=1e-8 for all lags -> polyfit slope ~ 4.7e-16 for any history of >= ~22 bars.
    # We evaluate the verbatim function once on a long series to get that constant; checked on every sampled pair.
    sk = r.rolling(63).skew().values
    H = HURST_CONST
    hb = (H < 0.4) & (sk > 1); hs = (H < 0.4) & (sk < -1)
    sig_sa = np.where(hb, 1, np.where(hs, -1, 0)); conf_sa = np.where(sig_sa == 0, 0.5, (0.5 - H) * 2)
    return {"trend": (sig_tr, conf_tr), "mean_reversion": (sig_mr, conf_mr), "momentum": (sig_mo, conf_mo),
            "volatility": (sig_vo, conf_vo), "stat_arb": (sig_sa, conf_sa)}

def vec_combined(sc):
    ws = 0.0; tc = 0.0
    for k, (sg, cf) in sc.items():
        ws = ws + sg * W[k] * cf; tc = tc + W[k] * cf
    with np.errstate(invalid="ignore", divide="ignore"):
        fin = np.where(tc > 0, ws / tc, 0.0)   # NaN tc -> `>0` False -> 0, same as the python code
    sig = np.where(fin > 0.2, 1, np.where(fin < -0.2, -1, 0))
    return signed(sig, np.abs(fin))

def verbatim_scores(g):
    """g: one stock DataFrame cut at the date (DatetimeIndex 'Date' like prices_to_df). Verbatim functions."""
    fs = {"trend": T.calculate_trend_signals, "mean_reversion": T.calculate_mean_reversion_signals,
          "momentum": T.calculate_momentum_signals, "volatility": T.calculate_volatility_signals,
          "stat_arb": T.calculate_stat_arb_signals}
    sigs = {k: f(g.copy()) for k, f in fs.items()}
    conv = lambda s: {"bullish": 1, "neutral": 0, "bearish": -1}[s["signal"]] * float(s["confidence"]) if s["signal"] != "neutral" else 0.0
    out = {NAMES[k]: conv(v) for k, v in sigs.items()}
    out["aihf_combined"] = conv(T.weighted_signal_combination(sigs, W))
    return out

def prices_df(g):
    x = g[["date", "open", "high", "low", "close", "volume"]].copy()
    x.index = pd.to_datetime(x.pop("date")); x.index.name = "Date"
    return x

_p = pd.Series(np.cumsum(np.random.RandomState(0).randn(300)) + 100, index=pd.date_range("2020-01-01", periods=300))
HURST_CONST = float(T.calculate_hurst_exponent(_p))

def main():
    n_check = int(sys.argv[sys.argv.index("--n-check") + 1]) if "--n-check" in sys.argv else 300
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 7
    d = load_daily(stocks_only=True).sort_values(["symbol", "date"])
    cols = {}; frames = []
    for sym, g in d.groupby("symbol", sort=False):
        g = g.reset_index(drop=True)
        sc = vec_signals(g)
        o = pd.DataFrame({"symbol": sym, "date": g.date.values})
        for k, (sg, cf) in sc.items(): o[NAMES[k]] = signed(sg, cf)
        o["aihf_combined"] = vec_combined(sc)
        frames.append(o[(o.date >= LO) & (o.date <= HI)])
    P = pd.concat(frames, ignore_index=True)
    os.makedirs(os.path.join(ROOT, "results/preds"), exist_ok=True)
    for nm in list(NAMES.values()) + ["aihf_combined"]:
        P[["symbol", "date"]].assign(score=P[nm].values).to_parquet(os.path.join(ROOT, f"results/preds/{nm}_swing.parquet"), index=False)
    print("wrote preds", len(P), "rows; NaN scores:", {nm: int(P[nm].isna().sum()) for nm in P.columns[2:]})

    # equivalence / truncation test vs verbatim functions on data truncated at the date
    rng = random.Random(seed); idx = P.sample(n_check, random_state=seed)[["symbol", "date"]].values.tolist()
    # force a few edge cases: first 2024 day, last 2025 day
    idx[0] = [idx[0][0], LO if False else P.date.min()]; idx[1] = [idx[1][0], P.date.max()]
    by = {s: g for s, g in d.groupby("symbol")}
    diffs = {nm: [] for nm in P.columns[2:]}; sigflips = {nm: 0 for nm in diffs}
    Pi = P.set_index(["symbol", "date"])
    for sym, dt in idx:
        g = by[sym]; cut = prices_df(g[g.date <= dt])
        assert cut.index[-1] == pd.Timestamp(dt)
        v = verbatim_scores(cut)
        for nm, val in v.items():
            vec = Pi.loc[(sym, dt), nm]
            dif = abs(val - vec) if not (np.isnan(val) and np.isnan(vec)) else 0.0
            diffs[nm].append(dif)
    res = {nm: {"n": len(v), "max_abs_diff": float(np.nanmax(v)), "n_diff_gt_1e-9": int(np.sum(np.array(v) > 1e-9))} for nm, v in diffs.items()}
    print(json.dumps(res, indent=1))
    json.dump({"hurst_const": HURST_CONST, "pairs_checked": n_check, "seed": seed, "result": res},
              open(os.path.join(ROOT, "results/aihf_equivalence.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
