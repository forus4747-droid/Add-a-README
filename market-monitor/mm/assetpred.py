"""Predictions for every tracked asset with at least 10 years of daily history.

Two questions per asset and run:
  dd10_3m  : closes at least 10% below today's close at some point in the next 63 bars
  down_12m : closes lower 252 bars from now
p_base  = share of past days (whose outcome window had already ended) on which the event happened.
p_model = same share among past days with the same drawdown bucket (distance below the record close) and the
          same side of the 200-day average, shrunk toward p_base with 20 pseudo-days.
p_final = p_base + w * (p_model - p_base); w per question lives in state/weights.json (key asset_<question>).
Only data up to the as-of date is used. Ledger ids look like dd10_3m@NVDA.
"""
import hashlib
import json

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from . import assets, ledger, selfcorrect

QUESTIONS = {"dd10_3m": (63, "dd", -0.10), "down_12m": (252, "down", 0.0)}
TEXT = {"dd10_3m": "closes at least 10% below today's close at some point in the next 63 trading days",
        "down_12m": "closes lower 252 trading days (about 12 months) from now"}
MODEL_VERSION = "asset-1.0"
MIN_YEARS = 10
MIN_BARS = 1500
SHRINK = 20.0
EDGES = (-0.05, -0.10, -0.20, -0.30)       # drawdown-from-record buckets: <5% | 5-10 | 10-20 | 20-30 | 30%+ below the record
W_GRID = (0.0, 0.25, 0.5, 0.75, 1.0)
W_DEFAULT = 0.5
SPLIT = pd.Timestamp("2015-12-31")         # weight chosen on days up to here, later days are the holdout


def weight_key(q):
    return "asset_" + q


def eligible(s):
    return s is not None and len(s) >= MIN_BARS and (s.index[-1] - s.index[0]).days >= MIN_YEARS * 365


def split_id(question_id):
    """'dd10_3m@NVDA' -> ('dd10_3m', 'NVDA'); S&P model questions have no '@' -> (id, None)."""
    q, _, t = question_id.partition("@")
    return q, (t or None)


def _state(c):
    """(bucket, above200) per bar. above200 is -1 until 200 bars exist."""
    dd = c / np.maximum.accumulate(c) - 1
    bucket = np.digitize(-dd, [-e for e in EDGES])
    ma = pd.Series(c).rolling(200).mean().values
    above = np.where(np.isnan(ma), -1, (c > ma).astype(int))
    return dd, bucket, above


def _outcomes(c, q):
    """y[t] in {0,1} for bars whose window has ended, NaN otherwise."""
    h, kind, thr = QUESTIONS[q]
    n = len(c)
    y = np.full(n, np.nan)
    if n <= h:
        return y
    if kind == "down":
        y[: n - h] = (c[h:] < c[: n - h]).astype(float)
    else:
        mn = sliding_window_view(c, h + 1).min(axis=1) / c[: n - h] - 1
        y[: n - h] = (mn <= thr + 1e-12).astype(float)
    return y


def predict_one(c, q):
    """Probabilities for the last bar of close array c using only that array."""
    c = np.asarray(c, dtype=float)
    dd, bucket, above = _state(c)
    y = _outcomes(c, q)
    ok = ~np.isnan(y)
    base = float(y[ok].mean())
    same = ok & (bucket == bucket[-1]) & (above == above[-1]) & (above[-1] >= 0)
    n_c = int(same.sum())
    k = float(y[same].sum())
    cond = (k + SHRINK * base) / (n_c + SHRINK)
    return {"base": base, "cond": float(cond), "n_cond": n_c, "bucket": int(bucket[-1]), "above200": int(above[-1]),
            "n_matured": int(ok.sum()), "dd_now": float(dd[-1])}


def backtest_series(s, q):
    """Walk-forward base / conditional estimates for every day t (needs >=10 years behind t) using only rows
    whose outcome window ended by t. Returns DataFrame(date, y, base, cond)."""
    c = s.values.astype(float)
    n = len(c)
    h = QUESTIONS[q][0]
    dd, bucket, above = _state(c)
    y = _outcomes(c, q)
    valid = ~np.isnan(y)
    key = np.where(above >= 0, bucket * 2 + above, -1)
    cy = np.cumsum(np.where(valid, y, 0.0))
    cn = np.cumsum(valid.astype(float))
    t = np.arange(n)
    first = int(np.searchsorted(s.index, s.index[0] + pd.DateOffset(years=MIN_YEARS)))
    use = (t >= first) & (t <= n - 1 - h) & (key >= 0)
    ts = t[use]
    i = ts - h                                                    # last row whose outcome ended by t
    base = cy[i] / cn[i]
    cond = np.empty(len(ts))
    for kv in np.unique(key[ts]):
        m = key[ts] == kv
        ind = valid & (key == kv)
        cky, ckn = np.cumsum(np.where(ind, y, 0.0)), np.cumsum(ind.astype(float))
        cond[m] = (cky[i[m]] + SHRINK * base[m]) / (ckn[i[m]] + SHRINK)
    return pd.DataFrame({"date": s.index[ts], "y": y[ts], "base": base, "cond": cond})


def backtest(root=None, asof=None):
    """Pooled walk-forward check over all eligible assets: weight chosen on days up to 2015, holdout after.
    Returns {question: {...}} with by-class tables. Overlapping daily outcomes: n counts days, not episodes."""
    uni = assets.load_universe(root)
    frames = {q: [] for q in QUESTIONS}
    for a in uni:
        s = assets.load_series(a, root, asof)
        if not eligible(s):
            continue
        for q in QUESTIONS:
            f = backtest_series(s, q)
            f["ticker"], f["asset_class"] = a["ticker"], a["asset_class"]
            frames[q].append(f)
    out = {}
    for q, fr in frames.items():
        if not fr:
            continue
        d = pd.concat(fr, ignore_index=True)
        pre = d[d["date"] <= SPLIT]
        hold = d[d["date"] > SPLIT]

        def brier(x, w):
            p = x["base"] + w * (x["cond"] - x["base"])
            return float(((p - x["y"]) ** 2).mean()) if len(x) else None
        sc = {w: brier(pre, w) for w in W_GRID}
        w_pre = min(sc, key=lambda w: (sc[w] if sc[w] is not None else 9, abs(w - W_DEFAULT)))
        cls = {}
        for name, x in [("ALL", hold)] + [(k, v) for k, v in hold.groupby("asset_class")]:
            bm, bb = brier(x, w_pre), brier(x, 0.0)
            cls[name] = {"n_days": int(len(x)), "n_assets": int(x["ticker"].nunique()), "brier_model": bm,
                         "brier_base": bb, "skill": None if not bb else 1 - bm / bb}
        out[q] = {"w_chosen_pre_2016": w_pre, "brier_by_w_pre_2016": {str(k): v for k, v in sc.items()},
                  "holdout_2016_latest": cls}
    return out


def issue_all(rows, asof, weights, root=None):
    """Build and append predictions for this as-of date. rows: assets.build_table output (needs asset series).
    Returns (n_added, list of prediction dicts for reporting, skipped reasons)."""
    uni = {a["ticker"]: a for a in assets.load_universe(root)}
    preds, shown, skipped = [], [], {}
    for r in rows:
        a = uni[r["ticker"]]
        s = assets.load_series(a, root, asof)
        if not eligible(s):
            skipped[r["ticker"]] = "less than 10 years of daily history"
            continue
        if (pd.Timestamp(asof) - s.index[-1]).days > assets.STALE_ASSET_DAYS:
            skipped[r["ticker"]] = "stale data"
            continue
        c = s.values.astype(float)
        for q, (h, _, _) in QUESTIONS.items():
            p = predict_one(c, q)
            w = float(weights.get(weight_key(q), W_DEFAULT))
            pf = float(np.clip(p["base"] + w * (p["cond"] - p["base"]), 0, 1))
            fh = hashlib.sha256(json.dumps([r["ticker"], str(s.index[-1].date()), p["bucket"], p["above200"],
                                            p["n_cond"], round(p["dd_now"], 8)]).encode()).hexdigest()
            d = {"asof_date": str(asof), "question_id": f"{q}@{r['ticker']}", "horizon_days": h,
                 "resolve_after": str((pd.Timestamp(asof) + pd.offsets.BDay(h)).date()), "p_base": p["base"],
                 "p_model": p["cond"], "p_final": pf, "w": w, "model_version": MODEL_VERSION, "features_hash": fh}
            preds.append(d)
            shown.append(dict(d, ticker=r["ticker"], name=r["name"], asset_class=r["asset_class"], question=q,
                              n_cond=p["n_cond"], bucket=p["bucket"], above200=p["above200"], dd_now=p["dd_now"],
                              last_bar=str(s.index[-1].date())))
    n = ledger.issue(preds, root)
    return n, shown, skipped


def series_loader(root=None):
    """ticker -> full close Series (same basis as the universe flag), for resolving matured predictions."""
    uni = {a["ticker"]: a for a in assets.load_universe(root)}
    cache = {}

    def f(ticker):
        if ticker not in cache:
            cache[ticker] = assets.load_series(uni[ticker], root) if ticker in uni else None
        return cache[ticker]
    return f


def accuracy(root=None):
    """Live accuracy from resolved ledger rows: per question, per question x asset class, plus the S&P model
    questions. brier_model = forecast, brier_base = plain base rate, skill = 1 - model/base."""
    uni = {a["ticker"]: a["asset_class"] for a in assets.load_universe(root)}
    preds = {r["id"]: r for r in ledger.read_predictions(root)}
    res = {r["prediction_id"]: r for r in ledger.read_resolutions(root)}
    groups = {}
    for pid, r in preds.items():
        q, t = split_id(r["question_id"])
        cls = uni.get(t, "unknown") if t else "S&P model"
        for key in ([(q, "ALL"), (q, cls)] if t else [("sp500_" + q, cls)]):
            g = groups.setdefault(key, {"issued": 0, "bf": [], "bb": []})
            g["issued"] += 1
            if pid in res:
                g["bf"].append(float(res[pid]["brier_final"]))
                g["bb"].append(float(res[pid]["brier_base"]))
    out = []
    for (q, cls), g in sorted(groups.items()):
        n = len(g["bf"])
        bm = float(np.mean(g["bf"])) if n else None
        bb = float(np.mean(g["bb"])) if n else None
        out.append({"question": q, "asset_class": cls, "n_issued": g["issued"], "n_resolved": n,
                    "brier_model": bm, "brier_base": bb, "skill": (1 - bm / bb) if n and bb else None})
    return out
