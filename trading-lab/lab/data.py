"""Shared data loading. All paths under DATA. Nothing here can see 2026: it is not on disk until Step 5."""
import glob, os, pandas as pd
DATA = os.environ.get("LAB_DATA", "/home/user/trading-stack/data")
DOW = "AAPL AMGN AXP BA CAT CRM CSCO CVX DIS DOW GS HD HON IBM INTC JNJ JPM KO MCD MMM MRK MSFT NKE PG TRV UNH V VZ WBA WMT".split()
ETFS = "SPY QQQ IWM DIA XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC TLT IEF HYG GLD USO".split()
SPLITS = {"TRAIN": ("2016-01-01", "2023-12-31"), "DEV": ("2024-01-01", "2024-12-31"),
          "VAL": ("2025-01-01", "2025-12-31"), "SEALED": ("2026-01-01", "2026-12-31")}

def load_5min(sym):
    fs = sorted(glob.glob(f"{DATA}/5min/{sym}_5min_*.csv"))
    df = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    df["day"] = df.time_new_york.str[:10]; df["hm"] = df.time_new_york.str[11:]
    return df

def daily_from_5min(sym):
    m = load_5min(sym); g = m.groupby("day")
    return pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(),
                         "close": g.close.last(), "volume": g.volume.sum()}).reset_index().rename(columns={"day": "date"})

def load_daily(stocks_only=False):
    f = f"{DATA}/daily/daily_v2.parquet"  # v2 = stray closing prints repaired (reports/03_17)
    d = pd.read_parquet(f if os.path.exists(f) else f"{DATA}/daily/daily.parquet")
    return d[~d.symbol.isin(ETFS)] if stocks_only else d
