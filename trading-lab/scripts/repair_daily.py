"""Repair daily open/close that Alpaca's daily bars take from stray prints instead of the auctions.
For every trading day, one request per window for the whole universe (1-minute bars, adjustment=all):
  open window 09:30-09:34 ET, close window 15:58-16:04 ET.
Official price = volume-weighted price ('vw') of the highest-volume minute at 09:30-09:31 (open) or
16:00-16:02 (close) -- the auction minute. The daily value is replaced only if it differs from that by more
than 0.5%. Half-days (13:00 close) have no 16:00 auction minute and are left unchanged.
Writes daily/daily_v2.parquet and daily/repairs.csv (every change). Usage: repair_daily.py [END_DATE]"""
import sys, time, requests, pandas as pd, numpy as np
from concurrent.futures import ThreadPoolExecutor
D = "/home/user/trading-stack/data/daily"; TH = 0.005
H = {"APCA-API-KEY-ID": "proxy", "APCA-API-SECRET-KEY": "proxy"}
d = pd.read_parquet(f"{D}/daily.parquet"); syms = sorted(d.symbol.unique()); days = sorted(d.date.unique())

def get(day, t0, t1):
    s = pd.Timestamp(f"{day} {t0}", tz="America/New_York").tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    e = pd.Timestamp(f"{day} {t1}", tz="America/New_York").tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    rows, tok = [], None
    while True:
        p = dict(symbols=",".join(syms), timeframe="1Min", start=s, end=e, limit=10000, feed="sip", adjustment="all")
        if tok: p["page_token"] = tok
        for a in range(8):
            try:
                r = requests.get("https://data.alpaca.markets/v2/stocks/bars", params=p, headers=H, timeout=90)
                if r.status_code == 200: break
            except Exception: pass
            time.sleep(2 * (a + 1))
        else: raise RuntimeError(f"failed {day}")
        j = r.json()
        for sy, bs in (j.get("bars") or {}).items():
            rows += [(sy, b["t"], b["vw"], b["v"]) for b in bs]
        tok = j.get("next_page_token")
        if not tok: break
    return rows

def one(day):
    out = []
    for kind, t0, t1, a0, a1 in (("open", "09:30", "09:35", "09:30", "09:31"), ("close", "15:58", "16:05", "16:00", "16:02")):
        b = pd.DataFrame(get(day, t0, t1), columns=["symbol", "t", "vw", "v"])
        if b.empty: continue
        b["hm"] = pd.to_datetime(b.t, utc=True).dt.tz_convert("America/New_York").dt.strftime("%H:%M")
        b = b[(b.hm >= a0) & (b.hm <= a1)]
        if b.empty: continue
        b = b.loc[b.groupby("symbol").v.idxmax()]
        out.append(b.assign(date=day, kind=kind)[["symbol", "date", "kind", "vw", "v"]])
    return pd.concat(out) if out else None

with ThreadPoolExecutor(6) as ex: res = [r for r in ex.map(one, days) if r is not None]
a = pd.concat(res); a.to_parquet(f"{D}/auction_prices.parquet", index=False)
rep = []
for kind in ("open", "close"):
    m = d.merge(a[a.kind == kind][["symbol", "date", "vw", "v"]], on=["symbol", "date"], how="left")
    bad = m.vw.notna() & ((m[kind] / m.vw - 1).abs() > TH) & (m.v >= 1000)
    rep.append(m[bad][["symbol", "date"]].assign(field=kind, old=m[kind][bad], new=m.vw[bad], auction_volume=m.v[bad]))
    d[kind] = np.where(bad.values, m.vw.values, d[kind].values)
d["high"] = d[["open", "high", "close"]].max(axis=1); d["low"] = d[["open", "low", "close"]].min(axis=1)
rep = pd.concat(rep); rep.to_csv(f"{D}/repairs.csv", index=False); d.to_parquet(f"{D}/daily_v2.parquet", index=False)
print("days", len(days), "auction rows", len(a), "repairs", rep.groupby("field").size().to_dict(), "by year", rep.groupby(rep.date.str[:4]).size().to_dict())
