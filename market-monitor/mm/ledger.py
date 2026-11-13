"""Append-only prediction ledger with a sha256 hash chain, plus resolutions and scorecard."""
import csv
import hashlib
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import ROOT
from .targets import EVENTS, HORIZONS

PRED_COLS = ["id", "issued_at_utc", "asof_date", "question_id", "horizon_days", "resolve_after", "p_base",
             "p_model", "p_final", "w", "model_version", "features_hash", "prev_hash", "row_hash"]
RES_COLS = ["prediction_id", "resolved_at_utc", "outcome", "brier_final", "brier_base"]
GENESIS = "0" * 64


def _dir(root):
    d = os.path.join(root or ROOT, "ledger")
    os.makedirs(d, exist_ok=True)
    return d


def _paths(root):
    d = _dir(root)
    pp, rp = os.path.join(d, "predictions.csv"), os.path.join(d, "resolutions.csv")
    for path, cols in ((pp, PRED_COLS), (rp, RES_COLS)):
        if not os.path.exists(path):
            with open(path, "w", newline="") as f:
                csv.writer(f).writerow(cols)
    return pp, rp


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _row_hash(vals):
    return hashlib.sha256("|".join(vals[:-1]).encode()).hexdigest()


def _read(path, cols):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _append(path, cols, rows):
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(cols)
        for r in rows:
            w.writerow(r)


def read_predictions(root=None):
    return _read(_paths(root)[0], PRED_COLS)


def read_resolutions(root=None):
    return _read(_paths(root)[1], RES_COLS)


def fmt(x):
    return f"{float(x):.6f}"


def issue(preds, root=None, now=None):
    """preds: list of dicts (asof_date, question_id, horizon_days, resolve_after, p_base, p_model, p_final, w,
    model_version, features_hash). Skips (asof_date, question_id) pairs already in the ledger."""
    pp, _ = _paths(root)
    existing = read_predictions(root)
    seen = {(r["asof_date"], r["question_id"]) for r in existing}
    prev = existing[-1]["row_hash"] if existing else GENESIS
    now = now or _now()
    out, added = [], 0
    for p in preds:
        key = (str(p["asof_date"]), p["question_id"])
        if key in seen:
            continue
        seen.add(key)
        vals = [f"{p['asof_date']}:{p['question_id']}", now, str(p["asof_date"]), p["question_id"],
                str(int(p["horizon_days"])), str(p["resolve_after"]), fmt(p["p_base"]), fmt(p["p_model"]),
                fmt(p["p_final"]), f"{float(p['w']):.4f}", p["model_version"], p["features_hash"], prev, ""]
        vals[-1] = _row_hash(vals)
        prev = vals[-1]
        out.append(vals)
        added += 1
    if out:
        _append(pp, PRED_COLS, out)
    return added


def verify(root=None):
    """Recompute the hash chain. Returns (ok, message)."""
    rows = read_predictions(root)
    prev = GENESIS
    ids = set()
    for i, r in enumerate(rows):
        vals = [r[c] for c in PRED_COLS]
        if r["prev_hash"] != prev:
            return False, f"row {i + 1} ({r['id']}): prev_hash mismatch"
        if _row_hash(vals) != r["row_hash"]:
            return False, f"row {i + 1} ({r['id']}): row_hash mismatch"
        if r["id"] in ids:
            return False, f"row {i + 1}: duplicate id {r['id']}"
        ids.add(r["id"])
        prev = r["row_hash"]
    seen = set()
    for r in read_resolutions(root):
        if r["prediction_id"] not in ids:
            return False, f"resolution for unknown prediction {r['prediction_id']}"
        if r["prediction_id"] in seen:
            return False, f"duplicate resolution {r['prediction_id']}"
        seen.add(r["prediction_id"])
    return True, f"ok: {len(rows)} predictions, {len(seen)} resolutions"


def outcome_for(g, asof_date, question):
    """(outcome or None if not yet resolved). g: daily close Series."""
    lab, kind, thr = EVENTS[question]
    h = HORIZONS[lab]
    i = g.index.get_indexer([pd.Timestamp(asof_date)])[0]
    if i < 0 or i + h > len(g) - 1:
        return None
    c = g.values
    ret = c[i + h] / c[i] - 1
    mn = c[i:i + h + 1].min() / c[i] - 1
    if kind == "down":
        return float(ret < 0)
    return float(mn <= thr + 1e-12)


def resolve(g, root=None, now=None):
    _, rp = _paths(root)
    preds = read_predictions(root)
    done = {r["prediction_id"] for r in read_resolutions(root)}
    now = now or _now()
    out = []
    for r in preds:
        if r["id"] in done:
            continue
        o = outcome_for(g, r["asof_date"], r["question_id"])
        if o is None:
            continue
        pf, pb = float(r["p_final"]), float(r["p_base"])
        out.append([r["id"], now, f"{o:.0f}", f"{(pf - o) ** 2:.6f}", f"{(pb - o) ** 2:.6f}"])
    if out:
        _append(rp, RES_COLS, out)
    return len(out)


def scorecard(root=None):
    preds = read_predictions(root)
    res = {r["prediction_id"]: r for r in read_resolutions(root)}

    def agg(rows):
        n = len(rows)
        rr = [res[r["id"]] for r in rows if r["id"] in res]
        bf = float(np.mean([float(x["brier_final"]) for x in rr])) if rr else None
        bb = float(np.mean([float(x["brier_base"]) for x in rr])) if rr else None
        return {"n_issued": n, "n_resolved": len(rr), "n_pending": n - len(rr),
                "brier_final": bf, "brier_base": bb,
                "skill": (1 - bf / bb) if rr and bb and bb > 0 else None}

    by_q = {}
    for q in EVENTS:
        rows = [r for r in preds if r["question_id"] == q]
        if rows:
            by_q[q] = agg(rows)
    return {"overall": agg(preds), "by_question": by_q}
