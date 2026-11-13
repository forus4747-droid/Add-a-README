"""Nudge each question's shrinkage weight w by one 0.05 step per run, based on live resolved skill."""
import csv
import json
import os
from datetime import datetime, timezone

import numpy as np

from . import ROOT
from . import ledger
from .targets import EVENTS

STEP = 0.05
MIN_N = 20


def _paths(root):
    r = root or ROOT
    os.makedirs(os.path.join(r, "state"), exist_ok=True)
    os.makedirs(os.path.join(r, "ledger"), exist_ok=True)
    return os.path.join(r, "state", "weights.json"), os.path.join(r, "ledger", "changelog.csv")


def load_weights(root=None):
    wp, _ = _paths(root)
    try:
        return json.load(open(wp))
    except Exception:
        return {}


def save_weights(w, root=None):
    wp, _ = _paths(root)
    with open(wp, "w") as f:
        json.dump(w, f, indent=1, sort_keys=True)


def init_weights(defaults, root=None):
    """Fill missing questions with the backtest-chosen w (never overwrites existing state)."""
    w = load_weights(root)
    for q, v in defaults.items():
        w.setdefault(q, float(v))
    save_weights(w, root)
    return w


def run(root=None, now=None):
    wp, cp = _paths(root)
    w = load_weights(root)
    preds = {r["id"]: r for r in ledger.read_predictions(root)}
    res = ledger.read_resolutions(root)
    now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    changes = []
    for q in EVENTS:
        rr = [r for r in res if r["prediction_id"] in preds and preds[r["prediction_id"]]["question_id"] == q]
        if len(rr) < MIN_N or q not in w:
            continue
        bf = float(np.mean([float(r["brier_final"]) for r in rr]))
        bb = float(np.mean([float(r["brier_base"]) for r in rr]))
        if bb <= 0:
            continue
        skill = 1 - bf / bb
        old = float(w[q])
        new = min(1.0, max(0.0, old + (STEP if skill > 0 else -STEP)))
        w[q] = round(new, 4)
        changes.append([now, q, f"{old:.4f}", f"{new:.4f}", len(rr), f"{skill:.6f}"])
    if changes:
        new_file = not os.path.exists(cp) or os.path.getsize(cp) == 0
        with open(cp, "a", newline="") as f:
            wr = csv.writer(f)
            if new_file:
                wr.writerow(["timestamp", "question", "old_w", "new_w", "n", "live_skill"])
            wr.writerows(changes)
        save_weights(w, root)
    return changes
