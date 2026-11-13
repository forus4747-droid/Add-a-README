"""Forward-looking outcomes (labels). Never used as features."""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

HORIZONS = {"1m": 21, "3m": 63, "12m": 252}      # trading days
EVENTS = {   # question_id: (horizon label, kind, threshold)
    "down_1m": ("1m", "down", 0.0),
    "dd5_1m": ("1m", "dd", -0.05),
    "down_3m": ("3m", "down", 0.0),
    "dd10_3m": ("3m", "dd", -0.10),
    "down_12m": ("12m", "down", 0.0),
    "dd10_12m": ("12m", "dd", -0.10),
    "dd20_12m": ("12m", "dd", -0.20),
}


def event_horizon_days(q):
    return HORIZONS[EVENTS[q][0]]


def daily_forward(g):
    """DataFrame indexed like g: fwd_ret_h, fwd_min_h (min close over t..t+h divided by close_t, minus 1)."""
    c = g.values.astype(float)
    n = len(c)
    out = {}
    for lab, h in HORIZONS.items():
        r = np.full(n, np.nan)
        m = np.full(n, np.nan)
        if n > h:
            r[: n - h] = c[h:] / c[: n - h] - 1
            win = sliding_window_view(c, h + 1).min(axis=1)
            m[: n - h] = win / c[: n - h] - 1
        out[f"fwd_ret_{h}"] = r
        out[f"fwd_min_{h}"] = m
    return pd.DataFrame(out, index=g.index)


def event_value(row_ret, row_min, q):
    lab, kind, thr = EVENTS[q]
    if kind == "down":
        return np.where(np.isnan(row_ret), np.nan, (row_ret < 0).astype(float))
    return np.where(np.isnan(row_min), np.nan, (row_min <= thr + 1e-12).astype(float))


def month_targets(F, g):
    """Targets for each month-end row. Rows before the first daily close (pre-1928) are NaN.
    Also returns daily index position (idx) of each row, -1 if absent."""
    D = daily_forward(g)
    pos = g.index.get_indexer(pd.DatetimeIndex(F["date"]))
    T = pd.DataFrame(index=F.index)
    T["idx"] = pos
    for col in D.columns:
        v = np.where(pos >= 0, D[col].values[np.where(pos >= 0, pos, 0)], np.nan)
        T[col] = v
    for q, (lab, kind, thr) in EVENTS.items():
        h = HORIZONS[lab]
        T[q] = event_value(T[f"fwd_ret_{h}"].values, T[f"fwd_min_{h}"].values, q)
    # Shiller-style annualised real total returns (monthly series; dividends accrue D/12 per month)
    P = F["close"]
    d = F["div"] / 12.0
    nom = (P + d) / P.shift(1)
    real = nom / (F["cpi"] / F["cpi"].shift(1))
    lg = np.log(real)
    for yrs in (3, 5, 10):
        w = 12 * yrs
        s = lg.rolling(w, min_periods=w).sum().shift(-w)
        T[f"real_tr_{yrs}y"] = np.exp(s / yrs) - 1
    return T
