"""S&P 500 drawdown episodes (daily closes) and after-threshold forward returns."""
import numpy as np
import pandas as pd

THRESH = 0.199


def zigzag_rallies(c, x):
    """Count up-legs of at least x within closes c (starts at a peak, ends at the trough).
    A leg is confirmed when price rises x above the running low; it ends when price falls x from its
    high (or at the series end)."""
    if len(c) < 2:
        return 0
    n = 0
    state = "down"
    low = c[0]
    high = c[0]
    lo_leg = c[0]
    for p in c[1:]:
        if state == "down":
            if p < low:
                low = p
            elif p >= low * (1 + x):
                state = "up"
                lo_leg = low
                high = p
        else:
            if p > high:
                high = p
            elif p <= high * (1 - x):
                n += 1
                state = "down"
                low = p
    if state == "up" and high / lo_leg - 1 >= x:
        n += 1
    return n


def episodes(g, F=None, thresh=THRESH):
    c = g.values.astype(float)
    dates = g.index
    n = len(c)
    out = []
    p = 0
    i = 0
    while i < n:
        # i is a peak index (new running high)
        p = i
        j = i + 1
        while j < n and c[j] < c[p]:
            j += 1
        end = j if j < n else n          # j == first close >= peak (recovery) or n
        seg = c[p:end]
        t = p + int(np.argmin(seg))
        depth = c[t] / c[p] - 1
        if depth <= -thresh:
            rec = j if j < n else None
            cape = None
            if F is not None:
                per = dates[p].to_period("M")
                if per in F.index and not pd.isna(F.loc[per, "cape"]):
                    cape = float(F.loc[per, "cape"] * c[p] / F.loc[per, "close"])
            out.append({
                "peak_date": str(dates[p].date()), "peak_level": float(c[p]),
                "trough_date": str(dates[t].date()), "trough_level": float(c[t]),
                "depth": float(depth),
                "days_to_trough": int((dates[t] - dates[p]).days),
                "trading_days_to_trough": int(t - p),
                "recovered_date": str(dates[rec].date()) if rec is not None else None,
                "days_trough_to_recover": int((dates[rec] - dates[t]).days) if rec is not None else None,
                "days_peak_to_recover": int((dates[rec] - dates[p]).days) if rec is not None else None,
                "cape_at_peak": cape,
                "rallies_10pct": zigzag_rallies(c[p:t + 1], 0.10),
                "rallies_20pct": zigzag_rallies(c[p:t + 1], 0.20),
                "ongoing": rec is None,
                "_p": p, "_t": t,
            })
        i = j if j < n else n
    return out


def after_threshold(g, eps, thresholds=(0.20, 0.30, 0.40)):
    """For each episode and threshold: first close that is >= thr below the episode peak."""
    c = g.values.astype(float)
    dates = g.index
    rows = []
    for thr in thresholds:
        for e in eps:
            p, t = e["_p"], e["_t"]
            if e["depth"] > -thr:
                continue
            seg = c[p:t + 1] / c[p] - 1
            j = p + int(np.argmax(seg <= -thr + 1e-12))
            r = {"threshold": thr, "peak_date": e["peak_date"], "hit_date": str(dates[j].date()),
                 "hit_close": float(c[j]), "drawdown_at_hit": float(c[j] / c[p] - 1)}
            for yrs in (1, 3, 5):
                k = j + 252 * yrs
                r[f"fwd_ret_{yrs}y"] = float(c[k] / c[j] - 1) if k < len(c) else None
            r["further_fall_to_final_low"] = float(c[t] / c[j] - 1)
            r["days_to_final_low"] = int((dates[t] - dates[j]).days)
            r["final_low_date"] = str(dates[t].date())
            r["final_low_is_to_date"] = bool(e["ongoing"])
            rows.append(r)
    return rows


def strip(eps):
    return [{k: v for k, v in e.items() if not k.startswith("_")} for e in eps]
