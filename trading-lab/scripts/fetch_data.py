"""Rebuild the 'Day Trader Backtest Data' set from Alpaca: 5-min regular-hours bars, one CSV per symbol per year,
columns: symbol,time_utc,time_new_york,open,high,low,close,volume."""
import sys, time, requests, pandas as pd
from concurrent.futures import ThreadPoolExecutor
OUT = "/home/user/trading-stack/data/5min"
SYMS = sys.argv[1].split(",")
START, END = sys.argv[2], sys.argv[3]
FEED, ADJ = (sys.argv[4] if len(sys.argv) > 4 else "sip"), (sys.argv[5] if len(sys.argv) > 5 else "raw")
H = {"APCA-API-KEY-ID": "proxy", "APCA-API-SECRET-KEY": "proxy"}  # real keys injected by the network proxy
import os; os.makedirs(OUT, exist_ok=True)

def fetch(sym):
    try: return _fetch(sym)
    except Exception as e: return f"{sym}: ERROR {e}"

def _fetch(sym):
    rows, tok = [], None
    while True:
        p = dict(timeframe="5Min", start=START, end=END, limit=10000, feed=FEED, adjustment=ADJ)
        if tok: p["page_token"] = tok
        for a in range(5):
            r = requests.get(f"https://data.alpaca.markets/v2/stocks/{sym}/bars", params=p, headers=H, timeout=60)
            if r.status_code == 429: time.sleep(3 * (a + 1)); continue
            r.raise_for_status(); break
        j = r.json(); rows += j.get("bars") or []; tok = j.get("next_page_token")
        if not tok: break
    if not rows: return f"{sym}: no data"
    df = pd.DataFrame(rows)
    t = pd.to_datetime(df.t, utc=True); ny = t.dt.tz_convert("America/New_York")
    m = (ny.dt.time >= pd.Timestamp("09:30").time()) & (ny.dt.time < pd.Timestamp("16:00").time())
    df, t, ny = df[m], t[m], ny[m]
    out = pd.DataFrame({"symbol": sym, "time_utc": t.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "time_new_york": ny.dt.strftime("%Y-%m-%d %H:%M"), "open": df.o, "high": df.h,
        "low": df.l, "close": df.c, "volume": df.v.astype("int64")})
    for y, g in out.groupby(ny.dt.year):
        g.to_csv(f"{OUT}/{sym}_5min_{y}.csv", index=False)
    return f"{sym}: {len(out)} bars {out.time_new_york.iloc[0]} -> {out.time_new_york.iloc[-1]}"

with ThreadPoolExecutor(4) as ex:
    for s in ex.map(fetch, SYMS): print(s, flush=True)
