"""Change detection between weekly runs: state files that remember the previous run, alerts.json, history csv."""
import csv
import json
import os

from . import ROOT


def roll(name, asof, current, root=None, save=True):
    """Compare `current` ({key: value}) with the previous run's values stored in state/<name>.json.
    Re-running for the same as-of date compares against the same earlier run (state is not rolled twice).
    Returns (previous dict or None, previous as-of)."""
    path = os.path.join(root or ROOT, "state", name)
    try:
        st = json.load(open(path))
    except Exception:
        st = {}
    if st.get("asof") == str(asof):
        prev, prev_asof = st.get("prev"), st.get("prev_asof")
    else:
        prev, prev_asof = st.get("current"), st.get("asof")
    if save:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"asof": str(asof), "current": current, "prev_asof": prev_asof, "prev": prev}, f, indent=1,
                      sort_keys=True)
    return prev, prev_asof


def flips(prev, current):
    """Keys whose value differs from the previous run (keys missing before, or 'n/a', are not flips)."""
    if prev is None:
        return []
    out = []
    for k, v in current.items():
        o = prev.get(k)
        if o is not None and o != v and "n/a" not in (o, v):
            out.append({"signal": k, "from": o, "to": v})
    return out


def write_alerts(alerts, root=None):
    os.makedirs(os.path.join(root or ROOT, "state"), exist_ok=True)
    with open(os.path.join(root or ROOT, "state", "alerts.json"), "w") as f:
        json.dump(alerts, f, indent=1)


def what_changed_lines(al):
    """Plain-language lines for reports."""
    out = []
    prev = al.get("previous_asof")
    if not prev:
        out.append("First run with change tracking: nothing to compare with yet. Today's zones and signals are the baseline.")
    for z in al.get("zone_changes", []):
        verb = "moved into" if z["flag"] == "ENTERED" else "moved out of"
        deep = f"the {z['to_zone']}% zone" if z["flag"] == "ENTERED" else (f"the {z['from_zone']}% zone" + (f" (now in the {z['to_zone']}% zone)" if z["to_zone"] else ""))
        out.append(f"{z['flag']}: {z['name']} ({z['ticker']}) {verb} {deep}.")
    for s in al.get("signal_flips", []):
        out.append(f"Signal flip: {s['signal']} went {s['from']} to {s['to']}.")
    for r in al.get("new_resolved", []):
        out.append(f"Resolved {r['prediction_id']}: outcome {'yes' if r['outcome'] == '1' else 'no'}, "
                   f"forecast error {float(r['brier_final']):.3f} vs base rate {float(r['brier_base']):.3f}.")
    for w in al.get("weight_changes", []):
        out.append(f"Weight {w['question']} moved {w['old_w']} to {w['new_w']} (live skill {float(w['live_skill']):+.3f}, n={w['n']}).")
    for d in al.get("data_failures", []):
        out.append(f"Data problem: {d}")
    if prev and len(out) == 0:
        out.append(f"No zone, signal, resolution or weight changes since {prev}.")
    return out


def append_history(asof, rows, signals, root=None):
    """state/weekly_history.csv: one row per asset and per tested signal per weekly as-of date (replaces the same date)."""
    path = os.path.join(root or ROOT, "state", "weekly_history.csv")
    cols = ["asof", "kind", "key", "state", "value", "extra"]
    old = []
    if os.path.exists(path):
        with open(path, newline="") as f:
            old = [r for r in csv.DictReader(f) if r["asof"] != str(asof)]
    new = [{"asof": str(asof), "kind": "asset", "key": r["ticker"], "state": r["deepest_zone"],
            "value": round(r["pct_below_record"], 3), "extra": round(r["last_close"], 6)} for r in rows]
    new += [{"asof": str(asof), "kind": "signal", "key": s["signal"], "state": s["state"],
             "value": "" if s["value"] is None else round(s["value"], 6), "extra": ""} for s in signals]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(old + new)


def read_history(root=None):
    path = os.path.join(root or ROOT, "state", "weekly_history.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))
