"""Build Phase 2 panel from panel_raw.parquet: point-in-time universe flag, market table, and the tier files.
Usage: build_long_panel.py RAW_DIR  -> RAW_DIR/panel_full.parquet, market_full.parquet"""
import sys, pandas as pd, numpy as np
D = sys.argv[1]; p = pd.read_parquet(f"{D}/panel_raw.parquet").sort_values(["symbol", "date"]).reset_index(drop=True)
MK = [s for s in p.symbol.unique() if s.startswith("_")] + ["SPY", "QQQ", "IWM", "DIA", "TLT", "GLD", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
m = p[p.symbol.isin(MK)].pivot(index="date", columns="symbol", values="close").sort_index(); m.to_parquet(f"{D}/market_full.parquet")
s = p[~p.symbol.isin(MK)].copy(); g = s.groupby("symbol", sort=False)
ok = (s.high >= s.low) & (s.open > 0) & (s.volume >= 0)
s = s[ok].copy(); g = s.groupby("symbol", sort=False)
s["dv63"] = g.dollar_vol.rolling(63, min_periods=40).median().reset_index(level=0, drop=True); s["dv63"] = s.groupby("symbol", sort=False).dv63.shift(1)
s["age"] = g.cumcount()
elig = (s.age >= 252) & s.dv63.notna()
s["rk"] = s.dv63.where(elig).groupby(s.date).rank(ascending=False, method="first")
s["in_univ"] = (s.rk <= 1000).fillna(False)
keep = s.groupby("symbol").in_univ.any(); s = s[s.symbol.isin(keep[keep].index)].drop(columns=["dv63", "age", "rk"]).reset_index(drop=True)
s.to_parquet(f"{D}/panel_full.parquet", index=False)
u = s[s.in_univ].groupby(s.date.str[:4]).agg(avg_names_per_day=("symbol", lambda x: len(x) / s.loc[x.index, "date"].nunique()), distinct=("symbol", "nunique"))
print("symbols kept", s.symbol.nunique(), "rows", len(s), s.date.min(), s.date.max()); print(u.iloc[::3].round(0).to_string())
