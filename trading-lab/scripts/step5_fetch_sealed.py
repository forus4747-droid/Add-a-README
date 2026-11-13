"""Step 5: download the SEALED period (2026-01-01 .. 2026-11-12) into a separate data root, data_sealed/.
Daily: same 521 symbols, same settings as fetch_daily.py; closes repaired with the same v3 rule as Step 3.17.
Run once, after the final skill's code was committed (commit 42db323)."""
import sys, os, time, requests, pandas as pd, numpy as np
from concurrent.futures import ThreadPoolExecutor
SRC = "/home/user/trading-stack/data"; DST = "/home/user/trading-stack/data_sealed"; LO, HI = "2026-01-01", "2026-11-12"
H = {"APCA-API-KEY-ID": "proxy", "APCA-API-SECRET-KEY": "proxy"}; os.makedirs(f"{DST}/daily", exist_ok=True)
old = pd.read_parquet(f"{SRC}/daily/daily.parquet"); syms = sorted(old.symbol.unique())
def req(p):
    rows, tok = [], None
    while True:
        q = dict(p, limit=10000, feed="sip", adjustment="all");
        if tok: q["page_token"] = tok
        for a in range(8):
            try:
                r = requests.get("https://data.alpaca.markets/v2/stocks/bars", params=q, headers=H, timeout=90)
                if r.status_code == 200: break
            except Exception: pass
            time.sleep(2 * (a + 1))
        else: raise RuntimeError("failed")
        j = r.json(); rows += [(s, b) for s, bs in (j.get("bars") or {}).items() for b in bs]; tok = j.get("next_page_token")
        if not tok: return rows
new = []
for i in range(0, len(syms), 50):
    new += [(s, b["t"][:10], b["o"], b["h"], b["l"], b["c"], b["v"]) for s, b in req(dict(symbols=",".join(syms[i:i+50]), timeframe="1Day", start=LO, end=HI))]
new = pd.DataFrame(new, columns="symbol date open high low close volume".split()); assert new.date.min() >= LO and new.date.max() <= HI
d = pd.concat([old, new]).drop_duplicates(["symbol", "date"]).sort_values(["symbol", "date"]).reset_index(drop=True)
d.to_parquet(f"{DST}/daily/daily.parquet", index=False)
def auction(day):
    s = pd.Timestamp(f"{day} 15:58", tz="America/New_York").tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    e = pd.Timestamp(f"{day} 16:05", tz="America/New_York").tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    b = pd.DataFrame([(sy, x["t"], x["vw"], x["v"]) for sy, x in req(dict(symbols=",".join(syms), timeframe="1Min", start=s, end=e))], columns=["symbol", "t", "vw", "v"])
    if b.empty: return None
    b["hm"] = pd.to_datetime(b.t, utc=True).dt.tz_convert("America/New_York").dt.strftime("%H:%M"); b = b[(b.hm >= "16:00") & (b.hm <= "16:02")]
    if b.empty: return None
    return b.loc[b.groupby("symbol").v.idxmax()].assign(date=day, kind="close")[["symbol", "date", "kind", "vw", "v"]]
with ThreadPoolExecutor(6) as ex: A = [x for x in ex.map(auction, sorted(new.date.unique())) if x is not None]
a = pd.concat([pd.read_parquet(f"{SRC}/daily/auction_prices.parquet")] + A); a = a[a.kind == "close"]
m = d[["symbol", "date", "close", "volume"]].merge(a[["symbol", "date", "vw", "v"]], on=["symbol", "date"], how="left")
ratio = (m.close / m.vw).where(m.v >= 1000); base = ratio.groupby(m.symbol).transform(lambda s: s.rolling(21, center=True, min_periods=5).median())
bad = (((ratio / base - 1).abs() > 0.005) & (m.v >= 0.03 * m.volume)).fillna(False)
rep = pd.DataFrame({"symbol": m.symbol[bad], "date": m.date[bad], "old": m.close[bad], "new": (m.vw * base)[bad]})
d["close"] = np.where(bad.values, (m.vw * base).values, d.close.values); d["high"] = d[["open", "high", "close"]].max(axis=1); d["low"] = d[["open", "low", "close"]].min(axis=1)
d.to_parquet(f"{DST}/daily/daily_v2.parquet", index=False); rep[rep.date >= LO].to_csv(f"{DST}/daily/repairs_2026.csv", index=False)
print("daily rows 2026:", len(new), "symbols:", new.symbol.nunique(), "days:", new.date.nunique(), new.date.min(), new.date.max(), "| close repairs in 2026:", int((rep.date >= LO).sum()), "| total repairs", len(rep))
