"""Final skill — swing features. Every feature for day t uses only bars dated <= t (rolling windows, positive
shifts only). Feature ideas are the union of what the tested repos use (momentum/reversal/volatility/volume
from ML4T and Qlib Alpha158, RSI/Bollinger from ai-hedge-fund and Freqtrade), plus market-relative versions.
All features are ranked across stocks each day to [-0.5, 0.5], so no scaling statistics are ever fitted."""
import numpy as np, pandas as pd

def build(daily):
    """daily: DataFrame[symbol,date,open,high,low,close,volume] incl. SPY. Returns stocks-only feature frame."""
    d = daily.sort_values(["symbol", "date"]).reset_index(drop=True)
    g = d.groupby("symbol", sort=False)
    c, o, h, l, v = d.close, d.open, d.high, d.low, d.volume
    pc = g.close.shift(1); r1 = c / pc - 1; d["r1"] = r1
    spy = d[d.symbol == "SPY"].set_index("date").r1; d["mkt"] = d.date.map(spy)
    F = {}
    def roll(s, n, f): return getattr(s.groupby(d.symbol, sort=False).rolling(n, min_periods=max(5, n // 2)), f)().reset_index(level=0, drop=True)
    for n in (1, 2, 5, 10, 21, 63, 126, 252): F[f"ret{n}"] = c / g.close.shift(n) - 1
    F["mom_12_1"] = g.close.shift(21) / g.close.shift(252) - 1
    F["mom_6_1"] = g.close.shift(21) / g.close.shift(126) - 1
    F["gap"] = o / pc - 1; F["intraday"] = c / o - 1
    on = o / pc - 1; d["on"] = on; d["intra"] = c / o - 1
    F["overnight21"] = roll(d.on, 21, "sum"); F["intraday21"] = roll(d.intra, 21, "sum")
    for n in (5, 21, 63): F[f"vol{n}"] = roll(d.r1, n, "std")
    F["vol_ratio"] = F["vol5"] / F["vol63"]
    d["pk"] = np.log(h / l) ** 2; F["parkinson21"] = np.sqrt(roll(d.pk, 21, "mean"))
    d["dn"] = np.minimum(d.r1, 0) ** 2; F["downvol63"] = np.sqrt(roll(d.dn, 63, "mean"))
    F["skew63"] = roll(d.r1, 63, "skew"); F["maxret21"] = roll(d.r1, 21, "max"); F["minret21"] = roll(d.r1, 21, "min")
    rng = (h - l).replace(0, np.nan); d["clv"] = (c - l) / rng; F["clv"] = d.clv; F["clv5"] = roll(d.clv, 5, "mean")
    for n in (21, 252): F[f"dist_high{n}"] = c / roll(h, n, "max") - 1
    F["dist_low252"] = c / roll(l, 252, "min") - 1
    for n in (20, 50, 200): F[f"ma_dist{n}"] = c / roll(c, n, "mean") - 1
    d["up"] = np.maximum(c - pc, 0); d["dnm"] = np.maximum(pc - c, 0)
    F["rsi14"] = roll(d.up, 14, "mean") / (roll(d.up, 14, "mean") + roll(d.dnm, 14, "mean"))
    F["bb_pos"] = (c - roll(c, 20, "mean")) / roll(c, 20, "std")
    d["dv"] = c * v; F["dollar_vol63"] = roll(d.dv, 63, "mean"); F["rel_vol5"] = roll(v, 5, "mean") / roll(v, 63, "mean")
    F["rel_vol1"] = v / roll(v, 21, "mean"); d["ami"] = d.r1.abs() / d.dv; F["amihud21"] = roll(d.ami, 21, "mean")
    d["rv"] = d.r1 * np.sign(v / g.volume.shift(1) - 1); F["ret_x_volchg5"] = roll(d.rv, 5, "sum")
    # market-relative: beta and residual returns (rolling 63d OLS slope vs SPY)
    d["xy"] = d.r1 * d.mkt; d["xx"] = d.mkt ** 2
    mx, my = roll(d.mkt, 63, "mean"), roll(d.r1, 63, "mean")
    beta = (roll(d.xy, 63, "mean") - mx * my) / (roll(d.xx, 63, "mean") - mx ** 2)
    F["beta63"] = beta; d["res"] = d.r1 - beta.groupby(d.symbol, sort=False).shift(1) * d.mkt
    for n in (5, 21): F[f"res_ret{n}"] = roll(d.res, n, "sum")
    F["idio_vol63"] = roll(d.res, 63, "std")
    X = pd.DataFrame(F); X.insert(0, "date", d.date); X.insert(0, "symbol", d.symbol)
    X["vol63_raw"] = F["vol63"]
    from lab.data import ETFS
    X = X[~X.symbol.isin(ETFS)].replace([np.inf, -np.inf], np.nan)
    cols = [k for k in F]
    X[cols] = X.groupby("date")[cols].rank(pct=True) - 0.5
    X[cols] = X[cols].fillna(0.0)
    return X, cols

def add_training_label(X, daily):
    """Label for FITTING only: 5-day open-to-open forward return, demeaned across stocks that day, divided by
    the stock's own 63-day volatility, then ranked to [-0.5,0.5]. label_end = date the label becomes known."""
    d = daily.sort_values(["symbol", "date"]); g = d.groupby("symbol", sort=False)
    y = (g.open.shift(-6) / g.open.shift(-1) - 1).clip(-0.5, 0.5)
    lab = pd.DataFrame({"symbol": d.symbol, "date": d.date, "fwd": y, "label_end": g.date.shift(-6)})
    X = X.merge(lab, on=["symbol", "date"], how="left")
    z = (X.fwd - X.groupby("date").fwd.transform("mean")) / X.vol63_raw.clip(lower=0.005)
    X["label"] = z.groupby(X.date).rank(pct=True) - 0.5
    return X
