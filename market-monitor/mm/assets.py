"""Tracked-asset universe (config/assets.csv): record highs, buy zones, trend and per-zone history.

A "zone" z (percent) is the price record_high * (1 - z/100). Everything is computed from daily closes
dated on or before the run's as-of date (no look-ahead). Assets flagged use_adjclose use Yahoo's
distribution-adjusted close; the last adjusted value equals the last quoted close, so zone prices are
on today's quote scale.
"""
import csv
import json
import os

import numpy as np
import pandas as pd

from . import ROOT, data

DEFAULT_ZONES = (10, 20, 30, 40)
HORIZONS = {"1y": 252, "3y": 756, "5y": 1260}
STALE_ASSET_DAYS = 10


def load_universe(root=None):
    """List of dicts from config/assets.csv (zones parsed to a tuple of ints)."""
    p = os.path.join(root or ROOT, "config", "assets.csv")
    out = []
    with open(p, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = (r.get("ticker") or "").strip()
            if not t:
                continue
            z = (r.get("zones") or "").strip() or ",".join(str(x) for x in DEFAULT_ZONES)
            out.append({"ticker": t, "name": r["name"].strip(), "asset_class": r["asset_class"].strip(),
                        "currency": r["currency"].strip(), "use_adjclose": str(r.get("use_adjclose", "0")).strip() in ("1", "true", "True"),
                        "zones": tuple(int(x) for x in z.replace(";", ",").split(",") if x.strip()),
                        "note": (r.get("note") or "").strip()})
    return out


def load_series(a, root=None, asof=None):
    """Daily close Series for one asset (adjusted if flagged), cut at asof. None if missing."""
    s = data.load_yahoo_adj(a["ticker"], root) if a["use_adjclose"] else data.load_yahoo(a["ticker"], root)
    if s is None:
        return None
    s = s.dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    s = s[s > 0]
    if asof is not None:
        s = s[s.index <= pd.Timestamp(asof)]
    return s if len(s) else None


def zone_episodes(c, zones):
    """Per-zone history of one close array. An episode runs from a record close until the next record close.
    Returns {z: stats dict}. 'Further fall' and 'days to low' use completed episodes only (the open one has
    no final low); forward returns use any first cross that has enough later data."""
    c = np.asarray(c, dtype=float)
    n = len(c)
    out = {}
    if n < 2:
        return {z: _empty(z) for z in zones}
    runmax = np.maximum.accumulate(c)
    newhigh = np.ones(n, dtype=bool)
    newhigh[1:] = c[1:] > runmax[:-1]
    starts = np.nonzero(newhigh)[0]
    ends = np.append(starts[1:], n)
    epmin = np.minimum.reduceat(c, starts) / c[starts] - 1
    for z in zones:
        thr = -z / 100.0
        eps = np.nonzero(epmin <= thr + 1e-12)[0]
        further, days, fwd = [], [], {k: [] for k in HORIZONS}
        n_open = 0
        for e in eps:
            a, b = starts[e], ends[e]
            sub = c[a:b] / c[a] - 1
            j = a + int(np.argmax(sub <= thr + 1e-12))       # first close at or beyond the zone
            lo = a + int(np.argmin(c[a:b]))
            if b < n:                                       # completed episode
                further.append(c[lo] / c[j] - 1)
                days.append(lo - j)
            else:
                n_open += 1
            for k, h in HORIZONS.items():
                if j + h < n:
                    fwd[k].append(c[j + h] / c[j] - 1)
        st = {"zone": z, "n_episodes": int(len(eps)), "n_completed": int(len(further)), "n_open": int(n_open),
              "further_fall_median": _q(further, np.median), "further_fall_worst": _q(further, np.min),
              "days_to_low_median": _q(days, np.median)}
        for k in HORIZONS:
            v = fwd[k]
            st[f"fwd_{k}_n"] = len(v)
            st[f"fwd_{k}_median"] = _q(v, np.median)
            st[f"fwd_{k}_worst"] = _q(v, np.min)
            st[f"fwd_{k}_pct_positive"] = _q(v, lambda x: float(np.mean(np.asarray(x) > 0)))
        out[z] = st
    return out


def _q(v, f):
    return float(f(v)) if len(v) else None


def _empty(z):
    st = {"zone": z, "n_episodes": 0, "n_completed": 0, "n_open": 0, "further_fall_median": None,
          "further_fall_worst": None, "days_to_low_median": None}
    for k in HORIZONS:
        st.update({f"fwd_{k}_n": 0, f"fwd_{k}_median": None, f"fwd_{k}_worst": None, f"fwd_{k}_pct_positive": None})
    return st


def deepest_zone(dd_pct, zones):
    """Deepest zone (percent) whose price the last close has reached, 0 if none. dd_pct: positive percent below record."""
    hit = [z for z in zones if dd_pct >= z - 1e-9]
    return max(hit) if hit else 0


def compute_asset(a, s):
    """Metrics for one asset from its close Series s (already cut at asof)."""
    c = s.values.astype(float)
    last, last_d = float(c[-1]), s.index[-1]
    rec_i = int(np.argmax(c))        # first occurrence of the record close
    rec = float(c[rec_i])
    win = s[s.index > last_d - pd.Timedelta(days=365)]
    hi52 = float(win.max())
    below = (1 - last / rec) * 100
    zones = a["zones"]
    zprice = {z: rec * (1 - z / 100.0) for z in zones}
    zdist = {z: (last / zprice[z] - 1) * 100 for z in zones}      # negative once the zone is reached
    ma200 = float(np.mean(c[-200:])) if len(c) >= 200 else None
    prev = s[s.index < pd.Timestamp(year=last_d.year, month=1, day=1)]
    ytd = float(last / prev.iloc[-1] - 1) * 100 if len(prev) else None
    return {"ticker": a["ticker"], "name": a["name"], "asset_class": a["asset_class"], "currency": a["currency"],
            "last_close": last, "last_date": str(last_d.date()), "record_close": rec,
            "record_date": str(s.index[rec_i].date()), "high_52w": hi52, "pct_below_record": below,
            "pct_below_52w_high": (1 - last / hi52) * 100,
            "zone_prices": zprice, "zone_distance_pct": zdist, "deepest_zone": deepest_zone(below, zones),
            "ma200": ma200, "pct_vs_ma200": None if ma200 is None else (last / ma200 - 1) * 100,
            "ytd_pct": ytd, "history_start": str(s.index[0].date()), "n_bars": int(len(c)),
            "zone_history": zone_episodes(c, zones), "note": a["note"], "use_adjclose": a["use_adjclose"]}


def build_table(asof, root=None):
    """Compute all assets. Returns (rows, problems). Missing/stale series are reported, never filled."""
    rows, problems = [], []
    for a in load_universe(root):
        s = load_series(a, root, asof)
        if s is None:
            problems.append(f"{a['ticker']}: no data")
            continue
        age = (pd.Timestamp(asof) - s.index[-1]).days
        r = compute_asset(a, s)
        r["data_age_days"] = int(age)
        if age > STALE_ASSET_DAYS:
            problems.append(f"{a['ticker']}: last bar {r['last_date']} is {age} days before {asof}")
        rows.append(r)
    return rows, problems


# ---------- change detection against the previous run

def _state_path(root):
    return os.path.join(root or ROOT, "state", "zones_state.json")


def flag_changes(rows, asof, root=None, save=True):
    """Set r['flag'] to ENTERED / EXITED by comparing the deepest zone with the previous run's state.
    The state keeps the prior run's zones so re-running for the same as-of date gives the same flags."""
    try:
        st = json.load(open(_state_path(root)))
    except Exception:
        st = {}
    if st.get("asof") == str(asof):
        prev = st.get("prev_deepest")
        prev_asof = st.get("prev_asof")
    else:
        prev = st.get("deepest")
        prev_asof = st.get("asof")
    changes = []
    for r in rows:
        r["flag"] = ""
        if prev is None or r["ticker"] not in prev:
            continue
        old, new = int(prev[r["ticker"]]), int(r["deepest_zone"])
        if new > old:
            r["flag"] = "ENTERED"
        elif new < old:
            r["flag"] = "EXITED"
        if r["flag"]:
            changes.append({"ticker": r["ticker"], "name": r["name"], "flag": r["flag"], "from_zone": old, "to_zone": new})
    if save:
        os.makedirs(os.path.join(root or ROOT, "state"), exist_ok=True)
        with open(_state_path(root), "w") as f:
            json.dump({"asof": str(asof), "deepest": {r["ticker"]: int(r["deepest_zone"]) for r in rows},
                       "prev_asof": prev_asof, "prev_deepest": prev}, f, indent=1, sort_keys=True)
    return changes, prev_asof
