"""CLI: python -m mm.run weekly | backtest | verify | news FILE.json"""
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import MODEL_VERSION, ROOT
from . import data, features, targets, episodes, models, signals, ledger, selfcorrect, news, report

QUESTION_TEXT = {
    "down_1m": "S&P 500 closes lower 21 trading days (about 1 month) from now",
    "dd5_1m": "S&P 500 closes at least 5% below today's close at some point in the next 21 trading days",
    "down_3m": "S&P 500 closes lower 63 trading days (about 3 months) from now",
    "dd10_3m": "S&P 500 closes at least 10% below today's close at some point in the next 63 trading days",
    "down_12m": "S&P 500 closes lower 252 trading days (about 12 months) from now",
    "dd10_12m": "S&P 500 closes at least 10% below today's close at some point in the next 252 trading days",
    "dd20_12m": "S&P 500 closes at least 20% below today's close at some point in the next 252 trading days",
}
SNAPSHOT = ["^GSPC", "^IXIC", "NVDA", "GOOG", "XEQT.TO", "^GSPTSE", "CAD=X", "^TNX", "^IRX", "^VIX", "HYG",
            "BZ=F", "GC=F", "DX-Y.NYB", "BTC-USD"]


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if (math.isnan(o) or math.isinf(o)) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp, pd.Period)):
        return str(o.date()) if isinstance(o, pd.Timestamp) else str(o)
    if o is pd.NaT:
        return None
    return o


def snapshot(raw):
    out = {}
    for s in SNAPSHOT:
        ser = raw["yahoo"].get(s)
        if ser is None or ser.dropna().empty:
            out[s] = {"last_close": None, "note": "no data"}
            continue
        ser = ser.dropna()
        last_d = ser.index[-1]
        last = float(ser.iloc[-1])
        prev_year = ser[ser.index < pd.Timestamp(year=last_d.year, month=1, day=1)]
        ytd = float(last / prev_year.iloc[-1] - 1) if len(prev_year) else None
        win = ser[ser.index > last_d - pd.Timedelta(days=365)]
        hi = float(win.max())
        out[s] = {"last_close": last, "date": str(last_d.date()), "ytd_pct": None if ytd is None else ytd * 100,
                  "pct_from_52w_high": (last / hi - 1) * 100, "high_52w_close": hi}
    return out


def _fhash(row, asof, analog_cols):
    d = {c: (None if pd.isna(row[c]) else round(float(row[c]), 8)) for c in features.FEATURE_COLS}
    d["asof"] = str(asof)
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def weekly(root=None, refresh=True, quiet=False):
    root = root or ROOT
    t0 = time.time()
    log = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    manifest = data.refresh(root) if refresh else data.load_manifest(root)
    age = data.check_fresh(root)
    raw = data.load_all(root)
    F, g, info = features.build(raw)
    T = targets.month_targets(F, g)
    log(f"features built: {len(F)} months through {F.index[-1]} ({time.time() - t0:.1f}s)")
    bt, cached = models.backtest(F, T, g, root)
    log(f"backtest {'loaded from cache' if cached else 'computed'} ({time.time() - t0:.1f}s)")
    weights = selfcorrect.init_weights({q: r["w_all"] for q, r in bt.items()}, root)

    n_res = ledger.resolve(g, root)
    changes = selfcorrect.run(root)
    weights = selfcorrect.load_weights(root)

    asof = g.index[-1]
    row = F.iloc[-1]
    fh = _fhash(row, asof.date(), features.ANALOG_COLS)
    probs, issue_rows, skipped = {}, [], {}
    for q in targets.EVENTS:
        h = targets.event_horizon_days(q)
        lp = models.live_predict(F, T, q)
        if lp is None:
            skipped[q] = "no live prediction (missing analog features or too little resolved history)"
            continue
        w = float(weights.get(q, bt[q]["w_all"]))
        pf = float(models.final_p(lp["base"], lp["model"], w))
        probs[q] = dict(lp, final=pf, w=w)
        issue_rows.append({"asof_date": str(asof.date()), "question_id": q, "horizon_days": h,
                           "resolve_after": str((asof + pd.offsets.BDay(h)).date()), "p_base": lp["base"],
                           "p_model": lp["model"], "p_final": pf, "w": w, "model_version": MODEL_VERSION,
                           "features_hash": fh})
    n_issued = ledger.issue(issue_rows, root)
    ok, msg = ledger.verify(root)

    # ---- assemble latest.json
    eps = episodes.episodes(g, F)
    today_feat = {c: (None if pd.isna(row[c]) else float(row[c])) for c in features.FEATURE_COLS}
    ranks = features.percentile_ranks(F, row)
    qs = {}
    for q, r in bt.items():
        qs[q] = {"text": QUESTION_TEXT[q], "horizon_trading_days": targets.event_horizon_days(q),
                 "probabilities": probs.get(q), "skipped_reason": skipped.get(q),
                 "w_chosen_1950_1999": r["w_pre"], "w_chosen_all_data": r["w_all"],
                 "w_live": weights.get(q),
                 "walk_forward_1950_1999": r["pre_1950_1999"],
                 "holdout_2000_latest": r["holdout_2000_latest"],
                 "holdout_2000_latest_with_w_all": r["holdout_2000_latest_w_all"],
                 "walk_forward_all": r["all_w_all"]}
    man = {k: {kk: v.get(kk) for kk in ("status", "last_date", "rows", "first_date", "retrieved_at", "sha256", "error")}
           for k, v in manifest.items()}
    fred_ok = all(manifest.get(f"fred:{s}", {}).get("status") == "ok" for s in data.FRED_SERIES)
    latest = {
        "asof": str(asof.date()), "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_version": MODEL_VERSION, "sp500_last_close": float(g.iloc[-1]), "sp500_data_age_days": age,
        "manifest": {"sources": man, "n_ok": sum(1 for v in man.values() if v["status"] == "ok"),
                     "n_failed": sum(1 for v in man.values() if v["status"] != "ok"),
                     "failed": [k for k, v in man.items() if v["status"] != "ok"], "fred_reachable": fred_ok},
        "feature_info": dict(info, partial_month=bool(row["partial_month"]),
                             cape_is_estimate=bool(row["cape_is_estimate"]), feature_row_month=str(F.index[-1])),
        "features_today": today_feat, "feature_percentile_ranks": ranks,
        "questions": qs,
        "analogs": models.closest_analogs(F, T, 15),
        "cape_10y_real_return": models.cape_ten_year_estimate(F, T),
        "signals": signals.board(F, T, raw),
        "episodes": episodes.strip(eps),
        "after_threshold": episodes.after_threshold(g, eps),
        "scorecard": ledger.scorecard(root),
        "ledger": {"verify_ok": ok, "verify_message": msg, "predictions_issued_this_run": n_issued,
                   "resolved_this_run": n_res, "weight_changes_this_run": [
                       dict(zip(["timestamp", "question", "old_w", "new_w", "n", "live_skill"], c)) for c in changes]},
        "news": news.recent_accepted(root),
        "market_snapshot": snapshot(raw),
        "runtime_seconds": None,
    }
    latest["runtime_seconds"] = round(time.time() - t0, 1)
    os.makedirs(os.path.join(root, "state"), exist_ok=True)
    with open(os.path.join(root, "state", "latest.json"), "w") as f:
        json.dump(clean(latest), f, indent=1, allow_nan=False)
    with open(os.path.join(root, "REPORT.md"), "w") as f:
        f.write(report.render(json.load(open(os.path.join(root, "state", "latest.json")))))
    log(f"weekly done in {time.time() - t0:.1f}s; issued {n_issued}, resolved {n_res}; ledger: {msg}")
    return latest


def cmd_backtest(root=None):
    raw = data.load_all(root)
    F, g, info = features.build(raw)
    T = targets.month_targets(F, g)
    bt, _ = models.backtest(F, T, g, root, use_cache=False)
    for q, r in bt.items():
        for lab in ("pre_1950_1999", "holdout_2000_latest"):
            s = r[lab]
            print(f"{q:9s} {lab:20s} w={s['w']:.2f} n={s['n_months']} Bbase={s['brier_base']:.4f} "
                  f"Bana={s['brier_analog']:.4f} Blog={s['brier_logit']:.4f} Bfin={s['brier_final']:.4f} "
                  f"skill={s['skill_final']:+.3f} episodes={s['n_event_episodes']}")
        print(f"{'':9s} w_all={r['w_all']:.2f}")


def main(argv=None):
    a = (argv if argv is not None else sys.argv)[1:]
    if not a or a[0] not in ("weekly", "backtest", "verify", "news"):
        print(__doc__)
        return 2
    if a[0] == "weekly":
        weekly()
    elif a[0] == "backtest":
        cmd_backtest()
    elif a[0] == "verify":
        ok, msg = ledger.verify()
        print(("PASS " if ok else "FAIL ") + msg)
        return 0 if ok else 1
    elif a[0] == "news":
        items = json.load(open(a[1]))
        acc, rej = news.ingest(items)
        print(f"accepted {len(acc)}, rejected {len(rej)}")
        for it, r in rej:
            print(" rejected:", it.get("url") if isinstance(it, dict) else it, "-", r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
