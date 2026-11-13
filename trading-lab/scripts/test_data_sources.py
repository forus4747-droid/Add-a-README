"""Compare yfinance / OpenBB daily bars with trusted Alpaca SIP daily (split+div adjusted).
Run from trading-lab with the core python:  python scripts/test_data_sources.py [fetch|analyze|all]
HARD RULE: end date 2026-01-01 exclusive; any row >= 2026-01-01 is dropped on receipt and never stored.
Raw downloads are cached in $CACHE (outside the repo)."""
import os, sys, time, json, subprocess, pickle, warnings
import numpy as np, pandas as pd
sys.path.insert(0, os.getcwd())
from lab.data import load_daily, DOW
warnings.filterwarnings("ignore")
CACHE = os.environ.get("DS_CACHE", "/tmp/claude-0/ds_cache"); os.makedirs(CACHE, exist_ok=True)
SYMS = DOW + "SPY QQQ AMC NVDA TSLA GOOGL AMZN META".split()
START, END = "2016-01-04", "2026-01-01"   # END exclusive
LAST = "2025-12-31"
OBB_PY = "/home/user/trading-stack/envs/openbb/bin/python"
THR = 0.005

def clean(df):
    if len(df) == 0: return df
    df = df.copy(); df.index = pd.to_datetime(df.index).tz_localize(None) if df.index.tz is None else df.index.tz_localize(None)
    df.index = df.index.strftime("%Y-%m-%d"); return df[df.index <= LAST]   # drop 2026 immediately

def fetch():
    import yfinance as yf
    log = {"yfinance": yf.__version__, "errors": {}, "rows_dropped_2026": {}}
    for s in SYMS:
        for adj in (True, False):
            f = f"{CACHE}/{s}_{int(adj)}.pkl"
            if os.path.exists(f): continue
            try:
                df = yf.Ticker(s).history(start=START, end=END, auto_adjust=adj, actions=True, raise_errors=False)
                n = int((pd.to_datetime(df.index).tz_localize(None) >= "2026-01-01").sum()) if len(df) else 0
                log["rows_dropped_2026"][f"{s}_{adj}"] = n
                df = clean(df) if len(df) else df
            except Exception as e:
                log["errors"][f"{s}_{adj}"] = repr(e)[:200]; df = pd.DataFrame()
            pickle.dump(df, open(f, "wb")); time.sleep(1.0)
    # stability: repeat identical call for 3 symbols
    import yfinance as yf
    for s in ("AAPL", "WBA", "SPY"):
        f = f"{CACHE}/{s}_rep.pkl"
        if os.path.exists(f): continue
        df = yf.Ticker(s).history(start=START, end=END, auto_adjust=True, actions=True); pickle.dump(clean(df), open(f, "wb")); time.sleep(1.0)
    json.dump(log, open(f"{CACHE}/fetch_log.json", "w"), indent=1)

OBB_PROBE = r'''
import json, importlib.metadata as m
out = {"openbb": m.version("openbb"), "openbb_core": m.version("openbb-core"), "attempts": {}}
from openbb import obb
out["has_equity_router"] = hasattr(obb, "equity")
out["providers"] = list(obb.coverage.providers.keys())
out["yfinance_in_providers"] = "yfinance" in out["providers"]
try: import openbb_yfinance; out["openbb_yfinance_import"] = "ok"
except Exception as e: out["openbb_yfinance_import"] = repr(e)
def attempt(name, fn):
    try:
        r = fn(); df = r.to_df(); out["attempts"][name] = "ok rows=%d" % len(df)
    except Exception as e: out["attempts"][name] = repr(e)[:300]
attempt("obb.equity.price.historical(AAPL, 2016-01-04, 2025-12-31, provider=yfinance)",
        lambda: obb.equity.price.historical("AAPL", start_date="2016-01-04", end_date="2025-12-31", provider="yfinance"))
attempt("obb.cboe.equity.historical(AAPL, 2025-12-01..2025-12-31)",
        lambda: obb.cboe.equity.historical("AAPL", start_date="2025-12-01", end_date="2025-12-31"))
attempt("obb.tmx.equity.historical(AAPL, 2025-12-01..2025-12-31)",
        lambda: obb.tmx.equity.historical("AAPL", start_date="2025-12-01", end_date="2025-12-31"))
attempt("obb.nasdaq.equity.historical(AAPL, 2025-12-01..2025-12-31)",
        lambda: obb.nasdaq.equity.historical("AAPL", start_date="2025-12-01", end_date="2025-12-31"))
out["equity_historical_commands"] = [c for c in obb.coverage.commands if c.endswith("historical") and "equity" in c]
print("JSON" + json.dumps(out))
'''
def obb_probe():
    p = subprocess.run([OBB_PY, "-c", OBB_PROBE], capture_output=True, text=True, timeout=300)
    line = [l for l in p.stdout.splitlines() if l.startswith("JSON")]
    return json.loads(line[0][4:]) if line else {"error": (p.stderr or p.stdout)[-500:]}

def ld(s, adj):
    f = f"{CACHE}/{s}_{int(adj)}.pkl"; return pickle.load(open(f, "rb")) if os.path.exists(f) else pd.DataFrame()

def stats(d):
    d = d.dropna()
    if not len(d): return dict(median=np.nan, p99=np.nan, mx=np.nan, n_over=0, n=0)
    a = d.abs(); return dict(median=a.median(), p99=a.quantile(.99), mx=a.max(), n_over=int((a > THR).sum()), n=len(a))

def analyze():
    T = load_daily(); T = T[(T.date <= LAST)]
    obb = obb_probe(); json.dump(obb, open(f"{CACHE}/obb_probe.json", "w"), indent=1)
    summ, detail, mism, splits, notes = [], [], [], [], []
    for s in SYMS:
        t = T[T.symbol == s].set_index("date").sort_index()
        a, r = ld(s, True), ld(s, False)
        if t.empty: notes.append(f"{s}: not in trusted data")
        for src, y, price_col in (("yf_auto_adjust", a, "Close"), ("yf_adjclose_col", r, "Adj Close")):
            if y.empty or t.empty:
                summ.append(dict(source=src, symbol=s, days_compared=0, missing_days=np.nan, verdict="NO DATA" if y.empty else "NOT IN TRUSTED")); continue
            ty = y[price_col]
            ti, yi = set(t.index), set(y.index)
            miss_y = sorted(ti - yi); extra_y = sorted(yi - ti)
            com = sorted(ti & yi)
            tc, yc = t.loc[com, "close"], ty.loc[com]
            rt, ry = tc.pct_change(), yc.pct_change()
            dif = (ry - rt).dropna(); st = stats(dif)
            ratio = (yc / tc)
            lr = np.log(ratio).diff().dropna()
            steps = lr[lr.abs() > 0.003]
            rs, re_ = ratio.iloc[:20].median(), ratio.iloc[-20:].median()
            frac_ok = 1 - st["n_over"] / max(st["n"], 1)
            ok = frac_ok >= 0.995 and len(miss_y) == 0
            why = []
            if frac_ok < 0.995: why.append(f"{st['n_over']} days >0.5% ({frac_ok:.4%} ok)")
            if miss_y: why.append(f"{len(miss_y)} trusted days missing in source")
            row = dict(source=src, symbol=s, days_compared=st["n"], missing_days=len(miss_y), extra_days=len(extra_y),
                       median_abs_ret_diff=st["median"], p99=st["p99"], max=st["mx"], days_over_0_5pct=st["n_over"],
                       level_ratio_start=rs, level_ratio_end=re_, level_ratio_cv=float(ratio.std() / ratio.mean()),
                       level_steps_gt0_3pct=len(steps), verdict="accurate" if ok else "FAIL: " + "; ".join(why))
            summ.append(row)
            # mismatches
            div = r["Dividends"] if "Dividends" in r else pd.Series(dtype=float)
            spl = r["Stock Splits"] if "Stock Splits" in r else pd.Series(dtype=float)
            for d, v in dif[dif.abs() > THR].items():
                i = com.index(d); prev = com[i - 1]
                cause = "unknown"
                if d in spl.index and spl.get(d, 0) not in (0, np.nan) and spl.get(d, 0) != 0: cause = "split day"
                elif d in div.index and div.get(d, 0) > 0: cause = "ex-dividend day (adj. method)"
                elif prev in miss_y or any(prev < m < d for m in miss_y): cause = "gap: missing day in source"
                elif any(prev < e < d for e in extra_y): cause = "source has extra day"
                mism.append(dict(source=src, symbol=s, date=d, trusted_ret=rt[d], source_ret=ry[d], diff=v, trusted_close=tc[d], source_close=yc[d], cause=cause))
            for d in miss_y: mism.append(dict(source=src, symbol=s, date=d, cause="trusted day missing in source"))
            if src == "yf_auto_adjust":
                # OHLC on adjusted basis, volume
                dd = dict(symbol=s)
                for c in ("open", "high", "low"):
                    x = (y.loc[com, c.capitalize()].pct_change() - t.loc[com, c].pct_change()).dropna(); z = stats(x)
                    dd.update({f"{c}_ret_median": z["median"], f"{c}_ret_p99": z["p99"], f"{c}_ret_over0.5%": z["n_over"]})
                    lv = (y.loc[com, c.capitalize()] / t.loc[com, c]); dd[f"{c}_level_ratio_median"] = lv.median()
                vr = (y.loc[com, "Volume"] / t.loc[com, "volume"]).replace([np.inf], np.nan)
                dd.update(vol_ratio_median=vr.median(), vol_ratio_p05=vr.quantile(.05), vol_ratio_p95=vr.quantile(.95),
                          vol_zero_days=int((y.Volume == 0).sum()), nan_rows=int(y[["Open","High","Low","Close"]].isna().any(axis=1).sum()),
                          first_date=y.index.min(), last_date=y.index.max(), n_rows=len(y), trusted_rows=len(t))
                detail.append(dd)
        # splits: yfinance unadjusted
        if not r.empty and not t.empty:
            sp = r["Stock Splits"][r["Stock Splits"] > 0]
            com = sorted(set(t.index) & set(r.index))
            ur = r.loc[com, "Close"].pct_change(); tr_ = t.loc[com, "close"].pct_change()
            jump = (ur - tr_).dropna(); big = jump[jump.abs() > 0.15]
            for d, v in sp.items():
                splits.append(dict(symbol=s, kind="yf_declared_split", date=d, ratio=v, yf_unadj_ret=ur.get(d, np.nan), trusted_ret=tr_.get(d, np.nan)))
            for d, v in big.items():
                implied = (1 + ur[d]) / (1 + tr_[d])
                splits.append(dict(symbol=s, kind="unadj_vs_trusted_jump", date=d, ratio=1 / implied, yf_unadj_ret=ur[d], trusted_ret=tr_[d]))
            # unadjusted level vs trusted: unadj/adj factor (yf Adj Close/Close) and trusted
            # check that Adj Close/Close factor is monotone and ends at 1
            f = (r["Adj Close"] / r["Close"]); detail_f = dict(symbol=s, adj_factor_first=f.iloc[0], adj_factor_last=f.iloc[-1])
    # stability
    stab = []
    for s in ("AAPL", "WBA", "SPY"):
        a, b = ld(s, True), pickle.load(open(f"{CACHE}/{s}_rep.pkl", "rb"))
        if a.empty: stab.append(dict(symbol=s, note="no data")); continue
        com = a.index.intersection(b.index)
        stab.append(dict(symbol=s, rows_a=len(a), rows_b=len(b), max_abs_close_diff=float((a.loc[com, "Close"] - b.loc[com, "Close"]).abs().max()),
                         max_abs_vol_diff=float((a.loc[com, "Volume"] - b.loc[com, "Volume"]).abs().max())))
    S = pd.DataFrame(summ)
    # aggregated rows per source
    agg = []
    for src, g in S[S.days_compared > 0].groupby("source"):
        agg.append(dict(source=src, symbol="ALL(%d)" % len(g), days_compared=g.days_compared.sum(), missing_days=g.missing_days.sum(),
                        median_abs_ret_diff=g.median_abs_ret_diff.median(), p99=g.p99.median(), max=g["max"].max(), days_over_0_5pct=g.days_over_0_5pct.sum(),
                        level_ratio_start=g.level_ratio_start.median(), level_ratio_end=g.level_ratio_end.median(),
                        verdict=f"{(g.verdict=='accurate').sum()}/{len(g)} symbols accurate; pooled ok {1-g.days_over_0_5pct.sum()/g.days_compared.sum():.4%}"))
    ob = dict(source="openbb(yfinance provider)", symbol="ALL", days_compared=0, missing_days=np.nan,
              verdict="NOT TESTABLE: openbb 5.0.0 installed has no equity router / yfinance provider; see notes")
    out = pd.concat([pd.DataFrame(agg), S, pd.DataFrame([ob])], ignore_index=True)
    os.makedirs("results", exist_ok=True)
    out.to_csv("results/datasources_summary.csv", index=False)
    pd.DataFrame(detail).to_csv("results/datasources_ohlcv_detail.csv", index=False)
    pd.DataFrame(mism).to_csv("results/datasources_mismatches.csv", index=False)
    pd.DataFrame(splits).to_csv("results/datasources_splits.csv", index=False)
    pd.DataFrame(stab).to_csv("results/datasources_stability.csv", index=False)
    print(out.head(4).to_string()); print(obb); print(stab); print(notes)
    fl = json.load(open(f"{CACHE}/fetch_log.json")); print({k: v for k, v in fl.items() if k != "rows_dropped_2026"}, "dropped2026 total", sum(fl["rows_dropped_2026"].values()))

if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "all"
    if m in ("fetch", "all"): fetch()
    if m in ("analyze", "all"): analyze()
