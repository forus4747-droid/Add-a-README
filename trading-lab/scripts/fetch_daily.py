"""Build the daily universe WITHOUT using any data after 2022 to choose it, and without downloading 2026.
1. Candidates: currently listed common stocks from nasdaqtrader symbol files.
2. Rank by median daily dollar volume over 2022-07-01..2022-12-31 (before every test period). Keep top 500.
3. Add fixed ETF list + the 30 Dow symbols.
4. Download daily bars 2016-01-01..END (adjustment=all) -> data/daily/daily.parquet
Usage: fetch_daily.py END_DATE   (END_DATE = 2025-12-31 for Steps 1-4)"""
import sys, io, time, requests, pandas as pd
END = sys.argv[1]; OUT = "/home/user/trading-stack/data/daily"
H = {"APCA-API-KEY-ID": "proxy", "APCA-API-SECRET-KEY": "proxy"}
ETFS = "SPY QQQ IWM DIA XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC TLT IEF HYG GLD USO".split()
DOW = "AAPL AMGN AXP BA CAT CRM CSCO CVX DIS DOW GS HD HON IBM INTC JNJ JPM KO MCD MMM MRK MSFT NKE PG TRV UNH V VZ WBA WMT".split()
import os; os.makedirs(OUT, exist_ok=True)

def bars(symbols, start, end, adj):
    rows, tok = [], None
    while True:
        p = dict(symbols=",".join(symbols), timeframe="1Day", start=start, end=end, limit=10000, feed="sip", adjustment=adj)
        if tok: p["page_token"] = tok
        for a in range(6):
            try:
                r = requests.get("https://data.alpaca.markets/v2/stocks/bars", params=p, headers=H, timeout=90)
                if r.status_code == 200: break
            except Exception: pass
            time.sleep(2 * (a + 1))
        else: raise RuntimeError(f"failed {symbols[:3]} {r.status_code if 'r' in dir() else ''}")
        j = r.json()
        for s, bs in (j.get("bars") or {}).items():
            rows += [(s, b["t"][:10], b["o"], b["h"], b["l"], b["c"], b["v"]) for b in bs]
        tok = j.get("next_page_token")
        if not tok: break
    return rows

def listed():
    out = []
    for f, col in (("nasdaqlisted.txt", "Symbol"), ("otherlisted.txt", "ACT Symbol")):
        t = requests.get(f"https://www.nasdaqtrader.com/dynamic/SymDir/{f}", timeout=60).text
        d = pd.read_csv(io.StringIO(t), sep="|").iloc[:-1]
        d = d[(d["Test Issue"] == "N") & (d["ETF"] == "N")]
        out += [s for s in d[col].astype(str) if s.isalpha() and len(s) <= 5]
    return sorted(set(out))

cand = listed(); print("candidates", len(cand), flush=True)
rk = []
for i in range(0, len(cand), 200):
    rk += bars(cand[i:i+200], "2022-07-01", "2022-12-31", "raw")
rk = pd.DataFrame(rk, columns="symbol date open high low close volume".split())
rk["dv"] = rk.close * rk.volume
g = rk.groupby("symbol").dv.agg(["median", "count"])
g = g[g["count"] >= 100].sort_values("median", ascending=False)
top = list(g.index[:500])
g.head(500).to_csv(f"{OUT}/universe_rank_2022H2.csv")
uni = sorted(set(top) | set(ETFS) | set(DOW)); print("universe", len(uni), flush=True)
rows = []
for i in range(0, len(uni), 50):
    rows += bars(uni[i:i+50], "2016-01-01", END, "all"); print(i, len(rows), flush=True)
df = pd.DataFrame(rows, columns="symbol date open high low close volume".split()).sort_values(["symbol", "date"])
assert df.date.max() <= END
df.to_parquet(f"{OUT}/daily.parquet", index=False)
print("saved", len(df), df.date.min(), df.date.max(), df.symbol.nunique())
