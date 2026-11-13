"""Independent check of TA-Lib and pandas-ta against from-definition reference implementations.
Run from /home/user/Add-a-README/trading-lab:  PY scripts/test_indicators.py
References below use only numpy/pandas loops; they never call talib or pandas_ta."""
import os, sys, warnings, inspect, json
import numpy as np, pandas as pd
sys.path.insert(0, os.getcwd())
warnings.filterwarnings("ignore")
import talib, pandas_ta as ta
import lab.data as D

NAN = np.nan
N = 20
# ---------------------------------------------------------------- reference implementations
def r_sma(x, n):
    o = np.full(len(x), NAN)
    for i in range(n - 1, len(x)):
        o[i] = x[i - n + 1:i + 1].sum() / n
    return o

def r_ema(x, n, first=0, seed_from=None):
    """EMA alpha=2/(n+1); seeded at index first+n-1 with SMA of x[first:first+n] (StockCharts).
    seed_from lets the seed window end at first+n-1 but start elsewhere (TA-Lib MACD convention)."""
    o = np.full(len(x), NAN); k = 2.0 / (n + 1); s = first + n - 1
    a = first if seed_from is None else seed_from
    o[s] = x[a:a + n].sum() / n
    for i in range(s + 1, len(x)):
        o[i] = x[i] * k + o[i - 1] * (1 - k)
    return o

def r_wma(x, n):
    o = np.full(len(x), NAN); w = np.arange(1, n + 1, dtype=float)
    for i in range(n - 1, len(x)):
        o[i] = (w * x[i - n + 1:i + 1]).sum() / w.sum()
    return o

def r_rsi(c, n=14, seed="sma"):
    d = np.diff(c); g = np.maximum(d, 0); l = np.maximum(-d, 0)
    o = np.full(len(c), NAN)
    if seed == "sma":                       # Wilder 1978: first avg = simple mean of first n changes
        ag, al = g[:n].mean(), l[:n].mean(); start = n
        for i in range(n, len(c)):
            if i > n:
                ag = (ag * (n - 1) + g[i - 1]) / n; al = (al * (n - 1) + l[i - 1]) / n
            o[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    else:                                   # pandas ewm(alpha=1/n, adjust=False) seeded by first change
        ag, al = g[0], l[0]
        for i in range(1, len(c)):
            if i > 1:
                ag = (ag * (n - 1) + g[i - 1]) / n; al = (al * (n - 1) + l[i - 1]) / n
            o[i] = 100 * ag / (ag + al) if ag + al > 0 else NAN
    return o

def r_macd(c, f=12, s=26, g=9, conv="textbook"):
    if conv == "textbook":
        ef = r_ema(c, f)
    else:                                   # TA-Lib: fast EMA seeded at bar s-1 from the f bars ending there
        ef = np.full(len(c), NAN); k = 2.0 / (f + 1); ef[s - 1] = c[s - f:s].mean()
        for i in range(s, len(c)): ef[i] = c[i] * k + ef[i - 1] * (1 - k)
    es = r_ema(c, s); m = ef - es
    fv = int(np.argmax(~np.isnan(m)))
    sig = r_ema(m, g, first=fv)
    return m, sig, m - sig

def r_bb(c, n=20, k=2.0, ddof=0):
    mid = r_sma(c, n); sd = np.full(len(c), NAN)
    for i in range(n - 1, len(c)):
        w = c[i - n + 1:i + 1]; sd[i] = np.sqrt(((w - w.mean()) ** 2).sum() / (n - ddof))
    return mid + k * sd, mid, mid - k * sd

def true_range(h, l, c):
    tr = np.empty(len(c)); tr[0] = h[0] - l[0]
    for i in range(1, len(c)):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    return tr

def r_atr(h, l, c, n=14, tr0=False):
    """Wilder: ATR_n = mean of first n TR, then (prev*(n-1)+TR)/n.  tr0=True includes TR_0=H-L (StockCharts);
    tr0=False starts TR at bar 1 (needs previous close; Wilder's original, TA-Lib)."""
    tr = true_range(h, l, c); o = np.full(len(c), NAN)
    s = n - 1 if tr0 else n
    a = tr[s - n + 1:s + 1].mean(); o[s] = a
    for i in range(s + 1, len(c)):
        a = (a * (n - 1) + tr[i]) / n; o[i] = a
    return o

def dm_parts(h, l, c):
    up = np.diff(h); dn = -np.diff(l)
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = true_range(h, l, c)[1:]
    return pdm, mdm, tr

def r_adx(h, l, c, n=14):
    pdm, mdm, tr = dm_parts(h, l, c); m = len(c)
    sp, sm, st = pdm[:n].sum(), mdm[:n].sum(), tr[:n].sum()
    dx = np.full(m, NAN); pdi = np.full(m, NAN); mdi = np.full(m, NAN)
    for i in range(n, m):
        if i > n:
            sp = sp - sp / n + pdm[i - 1]; sm = sm - sm / n + mdm[i - 1]; st = st - st / n + tr[i - 1]
        pdi[i] = 100 * sp / st; mdi[i] = 100 * sm / st
        den = pdi[i] + mdi[i]; dx[i] = 100 * abs(pdi[i] - mdi[i]) / den if den != 0 else 0.0
    adx = np.full(m, NAN); a = dx[n:2 * n].mean(); adx[2 * n - 1] = a
    for i in range(2 * n, m):
        a = (a * (n - 1) + dx[i]) / n; adx[i] = a
    return adx, pdi, mdi

def r_adx_talib(h, l, c, n=14):
    """TA-Lib seed: Wilder sums seeded with only n-1 raw values, the n-th enters through the recursive step."""
    pdm, mdm, tr = dm_parts(h, l, c); m = len(c)
    sp, sm, st = pdm[:n - 1].sum(), mdm[:n - 1].sum(), tr[:n - 1].sum(); dx = np.full(m, NAN)
    for i in range(n, m):
        sp = sp - sp / n + pdm[i - 1]; sm = sm - sm / n + mdm[i - 1]; st = st - st / n + tr[i - 1]
        pi, mi = 100 * sp / st, 100 * sm / st; dx[i] = 100 * abs(pi - mi) / (pi + mi)
    adx = np.full(m, NAN); a = dx[n:2 * n].mean(); adx[2 * n - 1] = a
    for i in range(2 * n, m): a = (a * (n - 1) + dx[i]) / n; adx[i] = a
    return adx

def r_adx_pta_py(h, l, c, n=14):
    """pandas-ta pure path: ATR(n) from TA-Lib (talib flag not propagated), DM smoothed with ewm(alpha=1/n, adjust=False)
    seeded by first value (no Wilder seed), DX smoothed the same way from first valid DX."""
    atr = r_atr(h, l, c, n, tr0=False)   # pandas-ta's internal atr() call ends up on TA-Lib's ATR, which equals this
    up = np.r_[NAN, np.diff(h)]; dn = np.r_[NAN, -np.diff(l)]
    pos = np.where((up > dn) & (up > 0), up, 0.0); neg = np.where((dn > up) & (dn > 0), dn, 0.0); pos[0] = neg[0] = NAN
    rma = lambda x: pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().to_numpy()
    k = 100 / atr; dmp = k * rma(pos); dmn = k * rma(neg)
    return rma(100 * np.abs(dmp - dmn) / (dmp + dmn))

def roll_ext(x, n, fn):
    o = np.full(len(x), NAN)
    for i in range(n - 1, len(x)): o[i] = fn(x[i - n + 1:i + 1])
    return o

def r_stoch(h, l, c, k=14, ks=3, d=3):
    hh = roll_ext(h, k, np.max); ll = roll_ext(l, k, np.min)
    raw = 100 * (c - ll) / (hh - ll)
    fv = k - 1
    sk = np.full(len(c), NAN); sk[fv + ks - 1:] = r_sma(raw[fv:], ks)[ks - 1:]
    sd = np.full(len(c), NAN); f2 = fv + ks - 1; sd[f2 + d - 1:] = r_sma(sk[f2:], d)[d - 1:]
    return sk, sd

def r_cci(h, l, c, n=20, const=0.015):
    tp = (h + l + c) / 3; o = np.full(len(c), NAN)
    for i in range(n - 1, len(c)):
        w = tp[i - n + 1:i + 1]; m = w.mean(); md = np.abs(w - m).mean()
        o[i] = (tp[i] - m) / (const * md) if md != 0 else NAN
    return o

def r_cci_ptabug(h, l, c, n=20, const=0.015):   # pandas-ta pure-python expression, precedence as written
    tp = (h + l + c) / 3; o = np.full(len(c), NAN)
    for i in range(n - 1, len(c)):
        w = tp[i - n + 1:i + 1]; m = w.mean(); md = np.abs(w - m).mean()
        o[i] = tp[i] - m / (const * md)
    return o

def r_obv(c, v, first="vol"):
    o = np.zeros(len(c)); o[0] = v[0] if first == "vol" else NAN
    run = 0.0 if first != "vol" else v[0]
    for i in range(1, len(c)):
        run += v[i] if c[i] > c[i - 1] else (-v[i] if c[i] < c[i - 1] else 0.0); o[i] = run
    return o

def r_roc(c, n=10):
    o = np.full(len(c), NAN); o[n:] = 100 * (c[n:] / c[:-n] - 1); return o

def r_willr(h, l, c, n=14):
    return -100 * (roll_ext(h, n, np.max) - c) / (roll_ext(h, n, np.max) - roll_ext(l, n, np.min))

def r_mfi(h, l, c, v, n=14, tie="neutral", eps=1e-9):
    """Quong & Soudack / StockCharts MFI. Equal typical price (|dTP|<=eps, i.e. a tie up to float noise) is neutral
    (no flow); tie="neg" + eps=0 reproduces pandas-ta pure path (strict float compare, not-greater => negative)."""
    tp = (h + l + c) / 3; mf = tp * v; o = np.full(len(c), NAN)
    pos = np.zeros(len(c)); neg = np.zeros(len(c))
    for i in range(1, len(c)):
        dd = tp[i] - tp[i - 1]
        if dd > eps: pos[i] = mf[i]
        elif dd < -eps: neg[i] = mf[i]
        elif tie == "neg": neg[i] = mf[i]
    for i in range(n, len(c)):
        p, q = pos[i - n + 1:i + 1].sum(), neg[i - n + 1:i + 1].sum()
        o[i] = 100.0 if q == 0 else 100 - 100 / (1 + p / q)
    return o

def r_vwap(h, l, c, v, day):
    tp = (h + l + c) / 3; o = np.empty(len(c)); cpv = cv = 0.0; prev = None
    for i in range(len(c)):
        if day[i] != prev: cpv = cv = 0.0; prev = day[i]
        cpv += tp[i] * v[i]; cv += v[i]; o[i] = cpv / cv
    return o

# ---------------------------------------------------------------- library wrappers
def S(x, idx): return pd.Series(x, index=idx)
def arr(r):
    if r is None: raise RuntimeError("pandas_ta returned None")
    if isinstance(r, pd.DataFrame): return {c: r[c].to_numpy(float) for c in r.columns}
    if isinstance(r, pd.Series): return r.to_numpy(float)
    return np.asarray(r, float)

def lib_calls(df):
    """returns {indicator_component: {library: array or Exception}} using explicit params."""
    idx = df.index; o, h, l, c, v = (df[k].to_numpy(float) for k in "open high low close volume".split())
    cs, hs, ls, vs = (S(a, idx) for a in (c, h, l, v))
    out = {}
    def put(name, lib, fn):
        try: val = fn()
        except Exception as e: val = e
        out.setdefault(name, {})[lib] = val
    def comp(name, lib, fn, cols):
        try: r = fn()
        except Exception as e:
            if "NoneType" in str(e): e = RuntimeError("pandas_ta returned None")
            for k in cols: out.setdefault(k, {})[lib] = e
            return
        if isinstance(r, tuple):
            for k, a in zip(cols, r): out.setdefault(k, {})[lib] = np.asarray(a, float)
        elif r is None:
            for k in cols: out.setdefault(k, {})[lib] = RuntimeError("returned None")
        else:
            for k, col in zip(cols, r.columns if isinstance(r, pd.DataFrame) else [None]):
                out.setdefault(k, {})[lib] = arr(r[col])
    TL, PT, PF = "talib", "pandas_ta[talib=True]", "pandas_ta[talib=False]"
    put("SMA", TL, lambda: talib.SMA(c, 20)); put("EMA", TL, lambda: talib.EMA(c, 20)); put("WMA", TL, lambda: talib.WMA(c, 20))
    put("RSI", TL, lambda: talib.RSI(c, 14))
    comp("MACD", TL, lambda: talib.MACD(c, 12, 26, 9), ["MACD_line", "MACD_signal", "MACD_hist"])
    comp("BB", TL, lambda: talib.BBANDS(c, 20, 2, 2, 0), ["BB_upper", "BB_mid", "BB_lower"])
    put("ATR", TL, lambda: talib.ATR(h, l, c, 14)); put("ADX", TL, lambda: talib.ADX(h, l, c, 14))
    comp("STOCH", TL, lambda: talib.STOCH(h, l, c, 14, 3, 0, 3, 0), ["STOCH_k", "STOCH_d"])
    put("CCI", TL, lambda: talib.CCI(h, l, c, 20)); put("OBV", TL, lambda: talib.OBV(c, v))
    put("ROC", TL, lambda: talib.ROC(c, 10)); put("WILLR", TL, lambda: talib.WILLR(h, l, c, 14))
    put("MFI", TL, lambda: talib.MFI(h, l, c, v, 14))
    for lib, flag in ((PT, True), (PF, False)):
        put("SMA", lib, lambda: arr(ta.sma(cs, 20, talib=flag))); put("EMA", lib, lambda: arr(ta.ema(cs, 20, talib=flag)))
        put("WMA", lib, lambda: arr(ta.wma(cs, 20, talib=flag))); put("RSI", lib, lambda: arr(ta.rsi(cs, 14, talib=flag)))
        comp("MACD", lib, lambda: ta.macd(cs, 12, 26, 9, talib=flag)[[f"MACD_12_26_9", "MACDs_12_26_9", "MACDh_12_26_9"]], ["MACD_line", "MACD_signal", "MACD_hist"])
        comp("BB", lib, lambda: ta.bbands(cs, length=20, lower_std=2, upper_std=2, talib=flag)[["BBU_20_2_2", "BBM_20_2_2", "BBL_20_2_2"]], ["BB_upper", "BB_mid", "BB_lower"])
        put("ATR", lib, lambda: arr(ta.atr(hs, ls, cs, 14, talib=flag)))
        put("ADX", lib, lambda: arr(ta.adx(hs, ls, cs, 14, talib=flag)["ADX_14"]))
        comp("STOCH", lib, lambda: ta.stoch(hs, ls, cs, 14, 3, 3, talib=flag)[["STOCHk_14_3_3", "STOCHd_14_3_3"]], ["STOCH_k", "STOCH_d"])
        put("CCI", lib, lambda: arr(ta.cci(hs, ls, cs, 20, talib=flag))); put("OBV", lib, lambda: arr(ta.obv(cs, vs, talib=flag)))
        put("ROC", lib, lambda: arr(ta.roc(cs, 10, talib=flag))); put("WILLR", lib, lambda: arr(ta.willr(hs, ls, cs, 14, talib=flag)))
        put("MFI", lib, lambda: arr(ta.mfi(hs, ls, cs, vs, 14, talib=flag)))
    return out

def references(df):
    o, h, l, c, v = (df[k].to_numpy(float) for k in "open high low close volume".split())
    R = {"SMA": r_sma(c, 20), "EMA": r_ema(c, 20), "WMA": r_wma(c, 20), "RSI": r_rsi(c, 14)}
    R["MACD_line"], R["MACD_signal"], R["MACD_hist"] = r_macd(c)
    R["BB_upper"], R["BB_mid"], R["BB_lower"] = r_bb(c)
    R["ATR"] = r_atr(h, l, c, 14); R["ADX"] = r_adx(h, l, c, 14)[0]
    R["STOCH_k"], R["STOCH_d"] = r_stoch(h, l, c)
    R["CCI"] = r_cci(h, l, c); R["OBV"] = r_obv(c, v); R["ROC"] = r_roc(c); R["WILLR"] = r_willr(h, l, c)
    R["MFI"] = r_mfi(h, l, c, v)
    return R

PRICE_UNIT = {"SMA", "EMA", "WMA", "MACD_line", "MACD_signal", "MACD_hist", "BB_upper", "BB_mid", "BB_lower", "ATR"}
def tol_for(ind, c, ref):
    if ind in PRICE_UNIT: return 1e-6 * float(np.mean(np.abs(c)))
    if ind == "OBV": return 1e-8 * float(np.nanmax(np.abs(ref)))
    return 1e-6          # dimensionless 0-100 / percent scale indicators: 1e-6 absolute

def first_valid(a):
    ok = np.flatnonzero(~np.isnan(a)); return int(ok[0]) if len(ok) else -1

def compare(ref, lib, tol, last=1000):
    n = len(ref); both = ~np.isnan(ref) & ~np.isnan(lib)
    d = np.where(both, np.abs(ref - lib), NAN)
    lastm = np.zeros(n, bool); lastm[n - last:] = True
    rv = ~np.isnan(ref)
    nan_mis_last = int((rv & np.isnan(lib) & lastm).sum())
    den = np.maximum(np.abs(ref), 1e-8 * max(tol / 1e-6, 1.0))
    rel = np.where(both, np.abs(ref - lib) / den, NAN)
    exc = np.flatnonzero(d > tol)
    return dict(first_valid_ref=first_valid(ref), first_valid=first_valid(lib),
                n_lib_valid_before_ref=int((~np.isnan(lib) & np.isnan(ref)).sum()),
                n_lib_nan_where_ref_valid=int((rv & np.isnan(lib)).sum()),
                max_abs_diff_all=float(np.nanmax(d)) if both.any() else NAN,
                max_rel_diff_all=float(np.nanmax(rel)) if both.any() else NAN,
                max_abs_diff_last1000=float(np.nanmax(np.where(lastm, d, NAN))) if (both & lastm).any() else NAN,
                last_bar_exceeding_tol=int(exc[-1]) if len(exc) else -1, tol=tol,
                nan_mismatch_last1000=nan_mis_last)

# ---------------------------------------------------------------- cause table: how the library differs, and the
# adjusted reference that reproduces it.  value: (text, source, fn(df)->array)
def variants(df):
    o, h, l, c, v = (df[k].to_numpy(float) for k in "open high low close volume".split())
    V = {}
    V["MACD_talib_seed"] = r_macd(c, conv="talib")
    V["BB_ddof1"] = r_bb(c, ddof=1)
    V["RSI_ewm_firstchange"] = r_rsi(c, 14, seed="first")
    V["ATR_tr0"] = r_atr(h, l, c, 14, tr0=True)
    V["CCI_ptabug"] = r_cci_ptabug(h, l, c)
    V["OBV_nan0"] = r_obv(c, v, first="nan")
    V["MFI_tieneg"] = r_mfi(h, l, c, v, tie="neg", eps=0.0)
    V["ADX_talib_seed"] = r_adx_talib(h, l, c)
    V["ADX_pta_py"] = r_adx_pta_py(h, l, c)
    return V

# ---------------------------------------------------------------- main
def run():
    SYMS = ["AAPL", "KO", "AMC", "INTC", "SPY"]
    daily = D.load_daily(); rows = []; proofs = []; pair_rows = []
    versions = dict(talib_python=talib.__version__, talib_C=str(talib.__ta_version__), pandas_ta=ta.version if hasattr(ta, "version") else "?",
                    numpy=np.__version__, pandas=pd.__version__)
    # pure-python side data for diffs-proof
    for sym in SYMS:
        df = daily[daily.symbol == sym].sort_values("date").reset_index(drop=True)
        df.index = pd.to_datetime(df.date)
        R = references(df); V = variants(df); L = lib_calls(df); c = df.close.to_numpy(float)
        for ind, libs in L.items():
            for lib, val in libs.items():
                if isinstance(val, Exception):
                    rows.append(dict(indicator=ind, library=lib, symbol=sym, first_valid=-1, match=False, cause_if_not=f"EXCEPTION {type(val).__name__}: {val}")); continue
                tol = tol_for(ind, c, R[ind]); m = compare(R[ind], val, tol)
                m.update(indicator=ind, library=lib, symbol=sym, n=len(c))
                m["match"] = bool(m["max_abs_diff_last1000"] <= tol and m["nan_mismatch_last1000"] == 0)
                m["startup_only_diff"] = bool(m["match"] and m["max_abs_diff_all"] > tol)
                rows.append(m)
        # talib vs pandas_ta pairwise
        for ind, libs in L.items():
            tl = libs.get("talib")
            for lib in ("pandas_ta[talib=True]", "pandas_ta[talib=False]"):
                val = libs.get(lib)
                if isinstance(val, Exception) or isinstance(tl, Exception) or val is None: continue
                tol = tol_for(ind, c, R[ind]); m = compare(tl, val, tol)
                pair_rows.append(dict(indicator=ind, symbol=sym, pandas_ta_mode=lib, **{k: m[k] for k in ("first_valid_ref", "first_valid", "max_abs_diff_all", "max_rel_diff_all", "max_abs_diff_last1000", "last_bar_exceeding_tol", "tol")},
                                      match=bool(m["max_abs_diff_last1000"] <= tol and m["nan_mismatch_last1000"] == 0)))
        # proofs: adjusted reference vs the library output that mismatched
        PT, PF, TL = "pandas_ta[talib=True]", "pandas_ta[talib=False]", "talib"
        def prove(ind, lib, vname, vals):
            lv = L[ind][lib]
            if isinstance(lv, Exception): return
            tol = tol_for(ind, c, R[ind]); m = compare(vals, lv, tol)
            proofs.append(dict(indicator=ind, library=lib, symbol=sym, adjusted_reference=vname, tol=tol,
                               max_abs_diff_all_after_adjust=m["max_abs_diff_all"], max_abs_diff_last1000_after_adjust=m["max_abs_diff_last1000"],
                               first_valid_ref_adjusted=m["first_valid_ref"], first_valid_lib=m["first_valid"]))
        for ind, vals in zip(("MACD_line", "MACD_signal", "MACD_hist"), V["MACD_talib_seed"]):
            for lib in (TL, PT): prove(ind, lib, "MACD_talib_seed", vals)
        for ind, vals in zip(("BB_upper", "BB_mid", "BB_lower"), V["BB_ddof1"]): prove(ind, PF, "BB_ddof1", vals)
        prove("ADX", TL, "ADX_talib_seed", V["ADX_talib_seed"]); prove("ADX", PT, "ADX_talib_seed", V["ADX_talib_seed"])
        prove("ADX", PF, "ADX_pta_py", V["ADX_pta_py"])
        prove("RSI", PF, "RSI_ewm_firstchange", V["RSI_ewm_firstchange"])
        prove("ATR", PF, "ATR_tr0", V["ATR_tr0"])
        prove("CCI", PF, "CCI_ptabug", V["CCI_ptabug"])
        prove("OBV", PF, "OBV_nan0", V["OBV_nan0"])
        prove("MFI", PF, "MFI_tieneg", V["MFI_tieneg"])
    summ = pd.DataFrame(rows)
    return summ, pd.DataFrame(proofs), pd.DataFrame(pair_rows), versions

# ================================================================= part 2: causes, extras, edge cases, outputs
SP = "/home/user/trading-stack/envs/core/lib/python3.12/site-packages/pandas_ta/"
CAUSES = {
 ("MACD_line", "talib"): "start-up only: TA-Lib MACD seeds the FAST EMA at bar slow-1 with the SMA of fast-many bars ending there (ta_MACD.c: both EMAs started at the same index) instead of bars 0..fast-1; line/signal/hist also NaN until bar 33 (signal start). Decays (see last_bar_exceeding_tol). Proof: MACD_talib_seed",
 ("ADX", "talib"): "start-up only: TA-Lib ADX (ta_ADX.c) seeds Wilder sums of +DM/-DM/TR with n-1 raw values, the n-th enters through the recursive step; textbook seed is the sum of the first n. Decays. Proof: ADX_talib_seed",
 ("ATR", "pandas_ta[talib=False]"): "start-up only: " + SP + "volatility/atr.py:atr seeds with mean(TR[0:n]) incl. TR0=H-L (StockCharts) instead of TR[1..n] (Wilder/TA-Lib); first value one bar earlier. Decays. Proof: ATR_tr0",
 ("RSI", "pandas_ta[talib=False]"): "start-up + premature output: " + SP + "momentum/rsi.py uses rma() = ewm(alpha=1/n, adjust=False) (" + SP + "overlap/rma.py) seeded by the first change, not SMA of first n; values emitted from bar 1 (before warm-up). Decays. Proof: RSI_ewm_firstchange",
 ("ADX", "pandas_ta[talib=False]"): "start-up + premature output: " + SP + "trend/adx.py non-talib branch: ATR comes from TA-Lib anyway (talib flag not passed to atr()), DM and DX smoothed with ewm(alpha=1/n, adjust=False) seeded by first value (no Wilder sum seed, no mean-of-DX seed); output from bar 14 instead of 27. Decays. Proof: ADX_pta_py",
 ("BB_upper", "pandas_ta[talib=False]"): "PERSISTENT: " + SP + "volatility/bbands.py defaults ddof=1 in non-talib path (stdev ddof param, statistics/stdev.py); talib path (BBANDS) is population ddof=0, so the two modes of the same function disagree by factor sqrt(n/(n-1)). Bollinger/StockCharts use population SD. Proof: BB_ddof1",
 ("CCI", "pandas_ta[talib=False]"): "PERSISTENT BUG: " + SP + "momentum/cci.py non-talib branch computes tp - sma/(c*mad) (missing parentheses; should be (tp - sma)/(c*mad)). Output is garbage (O(price/c)). Proof: CCI_ptabug",
 ("OBV", "pandas_ta[talib=False]"): "PERSISTENT offset = volume[0] and NaN at bar 0: " + SP + "utils/_core.py:signed_series sets `initial = None` unconditionally, so sign.iloc[0]=NaN and cumsum skips bar 0 (TA-Lib starts OBV at volume[0]). Proof: OBV_nan0",
 ("MFI", "pandas_ta[talib=False]"): "PERSISTENT/intermittent: " + SP + "volume/mfi.py: where(tp > roll(tp), 1, -1) uses a strict float compare so equal typical prices are counted as NEGATIVE flow and float noise (|dTP|~1e-14 on true ties) decides the sign; TA-Lib/textbook treat ties as no flow (TA_IS_ZERO |x|<1e-8). Proof: MFI_tieneg",
}
for k in ("MACD_signal", "MACD_hist"):
    CAUSES[(k, "talib")] = CAUSES[("MACD_line", "talib")]
for k in ("MACD_line", "MACD_signal", "MACD_hist"):
    CAUSES[(k, "pandas_ta[talib=True]")] = CAUSES[("MACD_line", "talib")] + " (pandas-ta delegates to talib.MACD)"
CAUSES[("ADX", "pandas_ta[talib=True]")] = CAUSES[("ADX", "talib")] + " (pandas-ta delegates to talib.ADX)"
for k in ("BB_mid", "BB_lower"):
    CAUSES[(k, "pandas_ta[talib=False]")] = CAUSES[("BB_upper", "pandas_ta[talib=False]")]
WARM = {  # warm-up convention notes keyed by (indicator, library) -> text, added to all rows where first_valid != first_valid_ref
 ("MACD_line", "talib"): "TA-Lib returns MACD line only from bar 33 (ref/textbook: bar 25)",
 ("STOCH_k", "talib"): "TA-Lib returns slow %K only from bar 17 (ref: 15) because output is aligned with %D",
}

def pair_cols(): return ["indicator", "library", "symbol", "first_valid", "first_valid_ref", "max_abs_diff_all", "max_rel_diff_all",
                         "max_abs_diff_last1000", "last_bar_exceeding_tol", "tol", "n_lib_valid_before_ref", "match", "startup_only_diff", "cause_if_not"]

def finalize_summary(raw):
    def cause(r):
        if isinstance(r.get("cause_if_not"), str): return r["cause_if_not"]
        notes = []
        if (not r["match"]) or r.get("startup_only_diff"):
            notes.append(CAUSES.get((r["indicator"], r["library"]), "UNEXPLAINED"))
        if r["first_valid"] != r.get("first_valid_ref") and r["first_valid"] != -1:
            notes.append("first_valid differs from reference: " + WARM.get((r["indicator"], r["library"]), "warm-up convention differs (see cause text)"))
        return " | ".join(notes)
    raw = raw.copy(); raw["cause_if_not"] = raw.apply(cause, axis=1)
    return raw[[c for c in pair_cols() if c in raw.columns]]

def vwap_test():
    m = D.load_5min("MSFT"); rows = []
    ny = pd.to_datetime(m.time_new_york)
    h, l, c, v = (m[k].to_numpy(float) for k in "high low close volume".split())
    ref = r_vwap(h, l, c, v, m.day.to_numpy())
    variants_idx = {"naive_NY_index": pd.DatetimeIndex(ny),
                    "UTC_tz_aware_index": pd.DatetimeIndex(pd.to_datetime(m.time_utc, utc=True)),
                    "NY_tz_aware_index": pd.DatetimeIndex(pd.to_datetime(m.time_utc, utc=True).dt.tz_convert("America/New_York"))}
    for name, idx in variants_idx.items():
        try:
            r = ta.vwap(pd.Series(h, idx), pd.Series(l, idx), pd.Series(c, idx), pd.Series(v, idx), anchor="D")
            lib = r.to_numpy(float) if r is not None else None
        except Exception as e:
            lib = e
        if lib is None or isinstance(lib, Exception):
            rows.append(dict(indicator="VWAP", library="pandas_ta", symbol="MSFT_5min", index_variant=name, first_valid=-1, match=False,
                             cause_if_not=f"no output: {lib}")); continue
        tol = 1e-6 * float(np.mean(c)); mm = compare(ref, lib, tol)
        rows.append(dict(indicator="VWAP", library="pandas_ta", symbol="MSFT_5min", index_variant=name, bars=len(c), tol=tol,
                         first_valid=mm["first_valid"], first_valid_ref=mm["first_valid_ref"], max_abs_diff_all=mm["max_abs_diff_all"],
                         max_rel_diff_all=mm["max_rel_diff_all"], max_abs_diff_last1000=mm["max_abs_diff_last1000"],
                         match=bool(mm["max_abs_diff_last1000"] <= tol and mm["max_abs_diff_all"] <= tol),
                         cause_if_not="" if mm["max_abs_diff_all"] <= tol else "anchor grouping differs from NY session date"))
    return pd.DataFrame(rows)

def summarize_series(a):
    if isinstance(a, Exception): return dict(status="EXCEPTION", detail=f"{type(a).__name__}: {a}")
    n = len(a); fin = np.isfinite(a)
    return dict(status="ok", n=n, n_nan=int(np.isnan(a).sum()), n_inf=int(np.isinf(a).sum()), first_valid=first_valid(a),
                last_value=(float(a[-1]) if n else NAN), n_valid=int(fin.sum()), n_zero_valid=int((a[fin] == 0).sum()))

def edge_cases():
    rs = np.random.RandomState(7); rows = []
    def mk(n, kind):
        idx = pd.date_range("2020-01-01", periods=n, freq="B")
        if kind == "const":
            c = np.full(n, 100.0); h = c.copy(); l = c.copy(); o = c.copy(); v = np.full(n, 1000.0)
        else:
            c = 100 + np.cumsum(rs.randn(n)); h = c + rs.rand(n); l = c - rs.rand(n); o = c; v = rs.randint(1000, 5000, n).astype(float)
        return pd.DataFrame(dict(open=o, high=h, low=l, close=c, volume=v), index=idx)
    cases = {"constant_price_300": mk(300, "const"), "short_len5": mk(5, "rw"), "short_len19": mk(19, "rw"), "short_len20": mk(20, "rw")}
    g = mk(300, "rw"); gi = 150; gf = g.copy(); gf.iloc[gi] = gf.iloc[gi - 1]; g.iloc[gi] = NAN; cases["nan_at_bar150_of_300"] = g
    LF = lib_calls(gf)   # same series with the NaN bar forward-filled: a sane-behaviour yardstick for contamination
    for cname, df in cases.items():
        L = lib_calls(df)
        for ind, libs in L.items():
            for lib, val in libs.items():
                d = summarize_series(val); d.update(case=cname, indicator=ind, library=lib)
                if cname.startswith("nan_at") and not isinstance(val, Exception):
                    after = val[gi + 1:]; d["n_nan_after_gap"] = int(np.isnan(after).sum()); d["n_after_gap"] = len(after)
                    d["recovers_by_end"] = bool(np.isfinite(val[-1]))
                    d["nan_run_after_gap"] = int(np.argmax(np.isfinite(after))) if np.isfinite(after).any() else len(after)
                    ff = LF[ind][lib]; dd = np.abs(val - ff)[gi + 1:]
                    d["max_abs_diff_vs_ffilled_run_after_gap"] = float(np.nanmax(dd)) if np.isfinite(dd).any() else NAN
                    d["n_unique_values_last100"] = int(len(np.unique(np.round(val[-100:][np.isfinite(val[-100:])], 12))))
                rows.append(d)
    return pd.DataFrame(rows)

def extra_checks(daily):
    rows = []
    for sym in ["AAPL", "KO", "AMC", "INTC", "SPY"]:
        df = daily[daily.symbol == sym].sort_values("date").reset_index(drop=True); df.index = pd.to_datetime(df.date)
        h, l, c = (df[k].to_numpy(float) for k in "high low close".split()); hs, ls, cs = (pd.Series(a, df.index) for a in (h, l, c))
        def add(check, a, b, expect, note=""):
            both = ~np.isnan(a) & ~np.isnan(b); d = np.abs(a - b)[both]
            rows.append(dict(check=check, symbol=sym, max_abs_diff=float(d.max()) if len(d) else NAN, max_abs_diff_last1000=float(np.abs(a - b)[-1000:][both[-1000:]].max()), expected_equal=expect, note=note))
        # 1 stochastic with smooth_k != d (pandas-ta passes d as slowk period to STOCH)
        rk, rd = r_stoch(h, l, c, 14, 5, 3)
        t = talib.STOCH(h, l, c, 14, 5, 0, 3, 0)
        p1 = ta.stoch(hs, ls, cs, 14, 3, 5, talib=True); p0 = ta.stoch(hs, ls, cs, 14, 3, 5, talib=False)
        for nm, arrk, arrd in (("talib.STOCH(14,5,3)", t[0], t[1]), ("pandas_ta stoch(k=14,d=3,smooth_k=5) talib=True", p1.iloc[:, 0].to_numpy(float), p1.iloc[:, 1].to_numpy(float)),
                               ("pandas_ta stoch(k=14,d=3,smooth_k=5) talib=False", p0.iloc[:, 0].to_numpy(float), p0.iloc[:, 1].to_numpy(float))):
            add(f"STOCH smooth_k=5,d=3 slowK vs ref: {nm}", rk, arrk, True); add(f"STOCH smooth_k=5,d=3 slowD vs ref: {nm}", rd, arrd, True)
        # 2 ADX DMP/DMN semantics
        adx_, pdi, mdi = r_adx(h, l, c)
        a1 = ta.adx(hs, ls, cs, 14, talib=True); a0 = ta.adx(hs, ls, cs, 14, talib=False)
        add("ADX DMP_14 (talib=True) vs reference +DI", pdi, a1["DMP_14"].to_numpy(float), True, "talib=True column is TA-Lib PLUS_DM (smoothed raw DM), not +DI")
        add("ADX DMP_14 (talib=False) vs reference +DI", pdi, a0["DMP_14"].to_numpy(float), True, "converges: DI from ewm-smoothed DM / ATR")
        add("ADX DMN_14 (talib=True) vs reference -DI", mdi, a1["DMN_14"].to_numpy(float), True)
        # 3 BB ddof options
        bu_p, bm_p, bl_p = r_bb(c, 20, 2.0, 0)
        b0 = ta.bbands(cs, length=20, lower_std=2, upper_std=2, ddof=0, talib=False)
        add("BBU pandas_ta talib=False ddof=0 vs ref ddof0", bu_p, b0["BBU_20_2_2"].to_numpy(float), True, "workaround")
        b1 = ta.bbands(cs, length=20, lower_std=2, upper_std=2, ddof=1, talib=True)
        add("BBU pandas_ta talib=True ddof=1 (ignored?) vs ref ddof0", bu_p, b1["BBU_20_2_2"].to_numpy(float), True, "ddof ignored when talib=True")
        # 4 pandas-ta default-parameter calls vs explicit
        bd = ta.bbands(cs)
        rows.append(dict(check="pandas_ta bbands() default call columns", symbol=sym, note=",".join(bd.columns), max_abs_diff=NAN, max_abs_diff_last1000=NAN, expected_equal=NAN))
        # 5 CCI pta_py vs ref with constant 0.015 and paren fix
        # 6 EMA presma=False
        e = ta.ema(cs, 20, talib=False, presma=False).to_numpy(float)
        add("EMA pandas_ta presma=False vs ref (SMA-seed)", r_ema(c, 20), e, True, "ewm seeded with first price; decays")
    return pd.DataFrame(rows)

def defaults_table():
    rows = []
    tmap = dict(SMA="SMA", EMA="EMA", WMA="WMA", RSI="RSI", MACD="MACD", BBANDS="BBANDS", ATR="ATR", ADX="ADX", STOCH="STOCH", CCI="CCI", OBV="OBV", ROC="ROC", WILLR="WILLR", MFI="MFI")
    pmap = dict(SMA=ta.sma, EMA=ta.ema, WMA=ta.wma, RSI=ta.rsi, MACD=ta.macd, BBANDS=ta.bbands, ATR=ta.atr, ADX=ta.adx, STOCH=ta.stoch, CCI=ta.cci, OBV=ta.obv, ROC=ta.roc, WILLR=ta.willr, MFI=ta.mfi)
    from talib import abstract
    for k, f in pmap.items():
        sig = inspect.signature(f)
        pd_ = {n: p.default for n, p in sig.parameters.items() if p.default is not inspect._empty and n not in ("offset", "kwargs")}
        rows.append(dict(indicator=k, talib_defaults=dict(abstract.Function(tmap[k]).parameters), pandas_ta_defaults_in_signature=pd_,
                         pandas_ta_effective=("length 10" if k in ("SMA", "EMA", "WMA") else "") ))
    return pd.DataFrame(rows)

def pandas_ta_effective_defaults(daily):
    """What pandas-ta really uses when called with no length (column names reveal it)."""
    df = daily[daily.symbol == "AAPL"].sort_values("date").reset_index(drop=True); cs = df.close; hs = df.high; ls = df.low; vs = df.volume
    out = {}
    out["sma"] = ta.sma(cs).name; out["ema"] = ta.ema(cs).name; out["wma"] = ta.wma(cs).name; out["rsi"] = ta.rsi(cs).name
    out["macd"] = list(ta.macd(cs).columns); out["bbands"] = list(ta.bbands(cs).columns); out["atr"] = ta.atr(hs, ls, cs).name
    out["adx"] = list(ta.adx(hs, ls, cs).columns); out["stoch"] = list(ta.stoch(hs, ls, cs).columns); out["cci"] = ta.cci(hs, ls, cs).name
    out["roc"] = ta.roc(cs).name; out["willr"] = ta.willr(hs, ls, cs).name; out["mfi"] = ta.mfi(hs, ls, cs, vs).name
    return out

def main2():
    os.makedirs("results", exist_ok=True)
    raw, proofs, pairs, versions = run()
    daily = D.load_daily()
    summary = finalize_summary(raw)
    vw = vwap_test()
    # append vwap (default index variant naive NY) to the summary
    vrow = vw[vw.index_variant == "naive_NY_index"].copy()
    summary = pd.concat([summary, vrow[[c for c in pair_cols() if c in vrow.columns]]], ignore_index=True)
    summary.to_csv("results/indicators_summary.csv", index=False)
    raw.to_csv("results/indicators_detail_raw.csv", index=False)
    proofs.to_csv("results/indicators_cause_proofs.csv", index=False)
    pairs.to_csv("results/indicators_talib_vs_pandasta.csv", index=False)
    vw.to_csv("results/indicators_vwap.csv", index=False)
    edge_cases().to_csv("results/indicators_edge_cases.csv", index=False)
    extra_checks(daily).to_csv("results/indicators_extra_checks.csv", index=False)
    defaults_table().to_csv("results/indicators_defaults.csv", index=False)
    json.dump(dict(versions=versions, pandas_ta_effective_default_names=pandas_ta_effective_defaults(daily)), open("results/indicators_versions.json", "w"), indent=1, default=str)
    pd.set_option("display.width", 250, "display.max_rows", 500, "display.max_columns", 30, "display.max_colwidth", 60)
    agg = summary.groupby(["indicator", "library"]).agg(first_valid=("first_valid", "max"), first_valid_ref=("first_valid_ref", "max"), max_abs_all=("max_abs_diff_all", "max"),
                    max_abs_last1000=("max_abs_diff_last1000", "max"), last_bar_exceeding=("last_bar_exceeding_tol", "max"), match=("match", "all"), startup_only=("startup_only_diff", "max"))
    agg.to_csv("results/indicators_summary_by_indicator_library.csv")
    print(agg); print(vw.drop(columns=["cause_if_not"]).to_string())
    print(proofs.groupby(["indicator", "library", "adjusted_reference"]).agg(all=("max_abs_diff_all_after_adjust", "max"), last=("max_abs_diff_last1000_after_adjust", "max"), tol=("tol", "max")))
    print("unexplained:", (summary.cause_if_not.str.contains("UNEXPLAINED")).sum())


if __name__ == "__main__":
    main2()
