"""Phase 2 data: daily bars 1990-01-01 .. END for every currently listed US common stock + market series,
from Yahoo's chart API. Prices are put on Yahoo's adjusted-close basis (splits + dividends):
factor = adjclose/close applied to open/high/low/close. Volume is Yahoo's split-adjusted share volume.
Usage: fetch_yahoo_long.py END_DATE OUT_DIR"""
import sys, io, time, requests, pandas as pd, numpy as np, concurrent.futures as cf
END, OUT = sys.argv[1], sys.argv[2]
P1 = int(pd.Timestamp("1990-01-01", tz="UTC").timestamp()); P2 = int((pd.Timestamp(END, tz="UTC") + pd.Timedelta(days=1)).timestamp())
MKT = {"SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM", "DIA": "DIA", "TLT": "TLT", "GLD": "GLD", "XLK": "XLK", "XLF": "XLF", "XLE": "XLE", "XLV": "XLV",
       "XLI": "XLI", "XLY": "XLY", "XLP": "XLP", "XLU": "XLU", "XLB": "XLB", "^GSPC": "_GSPC", "^VIX": "_VIX", "^TNX": "_TNX", "^IRX": "_IRX"}
def listed():
    out = []
    for f, col in (("nasdaqlisted.txt", "Symbol"), ("otherlisted.txt", "ACT Symbol")):
        d = pd.read_csv(io.StringIO(requests.get(f"https://www.nasdaqtrader.com/dynamic/SymDir/{f}", timeout=60).text), sep="|").iloc[:-1]
        d = d[(d["Test Issue"] == "N") & (d["ETF"] == "N")]; out += [s for s in d[col].astype(str) if s.isalpha() and len(s) <= 5]
    return sorted(set(out))
def get(sym):
    for a in range(5):
        try:
            r = requests.get(f"https://query{1 + a % 2}.finance.yahoo.com/v8/finance/chart/{sym}?period1={P1}&period2={P2}&interval=1d&events=div%2Csplits",
                             headers={"User-Agent": "Mozilla/5.0"}, timeout=40)
            if r.status_code == 404: return None
            if r.status_code == 200:
                x = r.json()["chart"]["result"][0]
                if "timestamp" not in x: return None
                q = x["indicators"]["quote"][0]; adj = x["indicators"]["adjclose"][0]["adjclose"]
                d = pd.DataFrame({"date": pd.to_datetime(x["timestamp"], unit="s", utc=True).tz_convert("America/New_York").strftime("%Y-%m-%d"),
                                  "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "adj": adj, "volume": q["volume"]}).dropna()
                d = d[(d.close > 0) & (d.date <= END)]
                f = d.adj / d.close
                for c in ("open", "high", "low"): d[c] = (d[c] * f).astype("float32")
                d["dollar_vol"] = (d.close * d.volume).astype("float32"); d["raw_close"] = d.close.astype("float32"); d["close"] = d.adj.astype("float32")
                d["volume"] = d.volume.astype("float32"); d.insert(0, "symbol", MKT.get(sym, sym))
                return d.drop(columns="adj").drop_duplicates("date")
        except Exception: pass
        time.sleep(1.5 * (a + 1))
    return "ERR"
syms = listed() + list(MKT); print("requesting", len(syms), flush=True)
res, err = [], []
with cf.ThreadPoolExecutor(8) as ex:
    for s, d in zip(syms, ex.map(get, syms)):
        if isinstance(d, str): err.append(s)
        elif d is not None and len(d) >= 60: res.append(d)
p = pd.concat(res, ignore_index=True); assert p.date.max() <= END
p.to_parquet(f"{OUT}/panel_raw.parquet", index=False)
print("symbols", p.symbol.nunique(), "rows", len(p), p.date.min(), p.date.max(), "errors", len(err), err[:20])
