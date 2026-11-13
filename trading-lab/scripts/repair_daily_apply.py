"""Apply the daily repair from saved auction prices (daily/auction_prices.parquet, built by repair_daily.py).
v1 of the rule compared levels directly and was WRONG: minute bars and daily bars carry different dividend
adjustment scales for some stocks (e.g. GSK, BP), so ~86,000 good values were flagged. Not used.
v2 rule (this file): ratio = daily price / auction price. Its 21-day centred rolling median per symbol is the
scale between the two series. A daily value is a stray print only if its ratio deviates from that median by
more than 0.5%; it is replaced by auction price x median ratio. Auction minute must have volume >= 1000.
v3 (final): CLOSES ONLY, and the auction minute must hold >= 3% of the day's volume. Chosen by validation against
Yahoo closes on 36 symbols (reports/03_17_data_repair.md): mismatching days 79 -> 49; opens untouched."""
import pandas as pd, numpy as np
D = "/home/user/trading-stack/data/daily"; TH = 0.005
d = pd.read_parquet(f"{D}/daily.parquet").sort_values(["symbol", "date"]).reset_index(drop=True)
a = pd.read_parquet(f"{D}/auction_prices.parquet"); rep = []
for kind in ("close",):  # opens are NOT repaired: validation showed Alpaca daily opens agree with Yahoo and the rule made them worse
    m = d[["symbol", "date", kind]].merge(a[a.kind == kind][["symbol", "date", "vw", "v"]], on=["symbol", "date"], how="left")
    assert (m.symbol.values == d.symbol.values).all() and (m.date.values == d.date.values).all()
    ratio = (m[kind] / m.vw).where(m.v >= 1000)
    base = ratio.groupby(m.symbol).transform(lambda s: s.rolling(21, center=True, min_periods=5).median())
    bad = (((ratio / base - 1).abs() > TH) & (m.v >= 0.03 * d.volume.values)).fillna(False)  # auction minute >= 3% of day volume
    new = m.vw * base
    rep.append(pd.DataFrame({"symbol": m.symbol[bad], "date": m.date[bad], "field": kind, "old": m[kind][bad], "new": new[bad], "auction_volume": m.v[bad]}))
    d[kind] = np.where(bad.values, new.values, d[kind].values)
d["high"] = d[["open", "high", "close"]].max(axis=1); d["low"] = d[["open", "low", "close"]].min(axis=1)
rep = pd.concat(rep); rep["change"] = rep.new / rep.old - 1
rep.to_csv(f"{D}/repairs.csv", index=False); d.to_parquet(f"{D}/daily_v2.parquet", index=False)
print("repairs", rep.groupby("field").size().to_dict()); print("by year", rep.groupby(rep.date.str[:4]).size().to_dict())
print("abs change: median %.4f  p90 %.4f  max %.4f" % (rep.change.abs().median(), rep.change.abs().quantile(.9), rep.change.abs().max()))
print("top symbols", rep.symbol.value_counts().head(6).to_dict())
print(rep[(rep.symbol == "TRV") & rep.date.between("2020-03-10", "2020-03-20")].round(3).to_string(index=False))
