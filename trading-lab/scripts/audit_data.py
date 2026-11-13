"""Step 1: data integrity audit. Writes reports/01_data_manifest.csv and results/01_audit.json."""
import glob, hashlib, json, os, pandas as pd, numpy as np
D = "/home/user/trading-stack/data"; res = {}; man = []
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
# ---- 5-min
rows = []
for f in sorted(glob.glob(f"{D}/5min/*.csv")):
    df = pd.read_csv(f); man.append((os.path.relpath(f, D), os.path.getsize(f), len(df), sha(f)))
    df["day"] = df.time_new_york.str[:10]
    bad = ((df.high < df[["open", "close", "low"]].max(axis=1)) | (df.low > df[["open", "close", "high"]].min(axis=1)) | (df[["open","high","low","close"]] <= 0).any(axis=1)).sum()
    per = df.groupby("day").size()
    rows.append(dict(file=os.path.basename(f), bars=len(df), days=len(per), full_days=int((per == 78).sum()),
        short_days=int((per < 78).sum()), dup=int(df.duplicated(["time_utc"]).sum()), bad_ohlc=int(bad),
        zero_vol=int((df.volume <= 0).sum()), nan=int(df.isna().sum().sum()), first=df.day.min(), last=df.day.max(),
        max_abs_bar_ret=float((df.close / df.open - 1).abs().max())))
a = pd.DataFrame(rows); a.to_csv("results/01_audit_5min.csv", index=False)
assert a["last"].max() <= "2025-12-31", "2026 data present!"
res["5min"] = dict(files=len(a), bars=int(a.bars.sum()), dup=int(a.dup.sum()), bad_ohlc=int(a.bad_ohlc.sum()),
    nan=int(a.nan.sum()), zero_vol=int(a.zero_vol.sum()), short_days=int(a.short_days.sum()), last=a["last"].max(),
    max_abs_bar_ret=float(a.max_abs_bar_ret.max()), worst_file=a.sort_values("max_abs_bar_ret").file.iloc[-1])
# ---- daily
p = f"{D}/daily/daily.parquet"
if os.path.exists(p):
    d = pd.read_parquet(p); man.append(("daily/daily.parquet", os.path.getsize(p), len(d), sha(p)))
    man.append(("daily/universe_rank_2022H2.csv", os.path.getsize(f"{D}/daily/universe_rank_2022H2.csv"), 500, sha(f"{D}/daily/universe_rank_2022H2.csv")))
    assert d.date.max() <= "2025-12-31", "2026 data present!"
    d["ret"] = d.groupby("symbol").close.pct_change()
    cal = d[d.symbol == "SPY"].date; n = d.groupby("symbol").date.agg(["min", "max", "count"])
    full = n[(n["min"] <= "2016-01-05")]
    bad = ((d.high < d[["open", "close", "low"]].max(axis=1) - 1e-6) | (d.low > d[["open", "close", "high"]].min(axis=1) + 1e-6) | (d.close <= 0)).sum()
    big = d[d.ret.abs() > 0.5][["symbol", "date", "ret"]]
    big.to_csv("results/01_audit_daily_big_moves.csv", index=False)
    # cross-check: daily built from 5-min vs daily file (split-adjusted vs all-adjusted => compare returns not levels)
    chk = []
    for s in ["MSFT", "HON", "KO", "WBA"]:
        m = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{D}/5min/{s}_5min_*.csv"))])
        dd = m.groupby(m.time_new_york.str[:10]).close.last().pct_change().dropna()
        x = d[d.symbol == s].set_index("date").ret.reindex(dd.index)
        chk.append(dict(symbol=s, days=len(dd), median_abs_diff=float((dd - x).abs().median()), p99_abs_diff=float((dd - x).abs().quantile(.99))))
    res["daily"] = dict(rows=len(d), symbols=int(d.symbol.nunique()), first=d.date.min(), last=d.date.max(),
        spy_days=len(cal), symbols_with_full_history=len(full), dup=int(d.duplicated(["symbol", "date"]).sum()),
        nan=int(d.drop(columns="ret").isna().sum().sum()), bad_ohlc=int(bad), moves_over_50pct=len(big),
        symbols_missing_days_vs_SPY=int((n["count"] < d[d.date >= "2023-01-01"].date.nunique()).sum()),
        fivemin_vs_daily_return_check=chk)
pd.DataFrame(man, columns=["file", "bytes", "rows", "sha256"]).to_csv("reports/01_data_manifest.csv", index=False)
json.dump(res, open("results/01_audit.json", "w"), indent=1); print(json.dumps(res, indent=1))
