"""Plain-assert sanity tests. Run: python -m tests.test_sanity   (uses cached data in data/raw)."""
import json
import os
import shutil
import sys
import tempfile
import traceback
from datetime import date

import numpy as np
import pandas as pd

from mm import ROOT, data, features, targets, episodes, ledger, selfcorrect, news, assets, signals, assetpred, run as runmod, changes

_cache = {}


def raw():
    if "raw" not in _cache:
        if not os.path.exists(os.path.join(ROOT, "data", "raw", "yahoo_^GSPC.csv")):
            data.refresh()
        _cache["raw"] = data.load_all()
    return _cache["raw"]


def gspc():
    return raw()["yahoo"]["^GSPC"]


def dd(peak, trough):
    g = gspc()
    return (g[trough] / g[peak] - 1) * 100


def test_drawdowns():
    g = gspc()
    cases = [("1929-09-16", "1932-06-01", -86.0, 1.5), ("2007-10-09", "2009-03-09", -56.8, 0.5),
             ("2000-03-24", "2002-10-09", -49.1, 0.5), ("1973-01-11", "1974-10-03", -48.2, 0.5),
             ("1987-08-25", "1987-12-04", -33.5, 0.5), ("2020-02-19", "2020-03-23", -33.9, 0.5)]
    eps = {(e["peak_date"], e["trough_date"]): e for e in episodes.episodes(g)}
    for p, t, exp, tol in cases:
        v = dd(p, t)
        assert abs(v - exp) <= tol, f"{p}->{t}: {v:.2f} vs {exp}"
        assert (p, t) in eps, f"episode detector missed {p}->{t}"
        assert abs(eps[(p, t)]["depth"] * 100 - v) < 1e-6
        # peak is the running maximum and trough the minimum of that window
        assert g[p] == g[:p].max() and g[t] == g[p:t].min()
    print("  drawdowns:", ", ".join(f"{p[:4]}:{dd(p, t):.1f}%" for p, t, _, _ in cases))


def test_shiller_pe10():
    sh = raw()["shiller"]
    a, b = sh.loc["1929-09-01", "PE10"], sh.loc["1999-12-01", "PE10"]
    assert abs(a - 32.6) <= 1.5 and abs(b - 44.0) <= 1.5, (a, b)
    print(f"  PE10 1929-09 {a:.1f}, 1999-12 {b:.1f}")


def test_no_lookahead():
    r = raw()
    F_full, _, _ = features.build(r)
    cols = features.FEATURE_COLS + ["close", "cape_is_estimate"]
    for cutoff in ("1975-06-30", "1999-12-31"):
        Ft, _, _ = features.build(features.truncate_raw(r, cutoff))
        cut = pd.Period(cutoff, "M")
        a = F_full.loc[:cut, cols].astype(float)
        b = Ft.loc[:cut, cols].astype(float)
        assert a.index.equals(b.index)
        pd.testing.assert_frame_equal(a, b, check_exact=False, rtol=1e-9, atol=1e-12)
        # targets use the future by design, but the feature table must not change anywhere in the past
    print("  features identical on truncated data (1975-06, 1999-12)")


def _synthetic_g(n=800, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-01-03", periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n))), index=idx)


def _pred(asof, q="down_1m", h=21, p=0.5, w=0.5):
    return {"asof_date": asof, "question_id": q, "horizon_days": h, "resolve_after": asof, "p_base": 0.4,
            "p_model": 0.5, "p_final": p, "w": w, "model_version": "t", "features_hash": "abc"}


def test_ledger_chain_and_idempotent():
    d = tempfile.mkdtemp()
    try:
        preds = [_pred("2020-01-31", q, 21) for q in targets.EVENTS]
        assert ledger.issue(preds, d) == 7
        ok, msg = ledger.verify(d)
        assert ok, msg
        assert ledger.issue(preds, d) == 0, "re-issue for same asof must not duplicate"
        assert len(ledger.read_predictions(d)) == 7
        assert ledger.issue([_pred("2020-02-07")], d) == 1
        assert ledger.verify(d)[0]
        # tamper detection
        p = os.path.join(d, "ledger", "predictions.csv")
        txt = open(p).read().replace("0.500000", "0.600000", 1)
        open(p, "w").write(txt)
        assert not ledger.verify(d)[0], "tampering must break the chain"
    finally:
        shutil.rmtree(d)
    print("  ledger chain verifies, idempotent, tamper detected")


def test_resolution_scorecard_selfcorrect():
    d = tempfile.mkdtemp()
    try:
        g = _synthetic_g()
        asofs = [str(g.index[i].date()) for i in range(0, 40)]
        outs = [ledger.outcome_for(g, a, "down_1m") for a in asofs]
        assert all(o is not None for o in outs)
        # informed forecasts (skill > 0)
        ledger.issue([_pred(a, p=0.9 if o == 1 else 0.1) for a, o in zip(asofs, outs)], d)
        # a prediction too recent to resolve
        late = str(g.index[-3].date())
        ledger.issue([_pred(late)], d)
        n = ledger.resolve(g, d)
        assert n == 40
        assert ledger.resolve(g, d) == 0
        sc = ledger.scorecard(d)
        assert sc["overall"]["n_pending"] == 1 and sc["by_question"]["down_1m"]["n_resolved"] == 40
        assert ledger.verify(d)[0]
        selfcorrect.save_weights({"down_1m": 0.5}, d)
        ch = selfcorrect.run(d)
        assert len(ch) == 1 and abs(selfcorrect.load_weights(d)["down_1m"] - 0.55) < 1e-9
        # uninformative/anti-informed forecasts (skill < 0) move w down by one step
        d2 = tempfile.mkdtemp()
        ledger.issue([_pred(a, p=0.1 if o == 1 else 0.9) for a, o in zip(asofs, outs)], d2)
        ledger.resolve(g, d2)
        selfcorrect.save_weights({"down_1m": 0.02}, d2)
        selfcorrect.run(d2)
        assert selfcorrect.load_weights(d2)["down_1m"] == 0.0, "clipped at 0"
        shutil.rmtree(d2)
        # fewer than 20 resolved: no change
        d3 = tempfile.mkdtemp()
        ledger.issue([_pred(a) for a in asofs[:10]], d3)
        ledger.resolve(g, d3)
        selfcorrect.save_weights({"down_1m": 0.5}, d3)
        assert selfcorrect.run(d3) == []
        shutil.rmtree(d3)
    finally:
        shutil.rmtree(d)
    print("  resolution, scorecard, self-correct step/clip/min-n OK")


def test_news_rules():
    d = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(d, "config"))
        shutil.copy(os.path.join(ROOT, "config", "allowlist.txt"), os.path.join(d, "config", "allowlist.txt"))
        today = date(2026, 11, 13)
        good = {"date": "2026-11-12", "url": "https://www.bls.gov/x", "source_domain": "bls.gov", "headline": "h",
                "tag": "inflation", "direction": "risk_up", "note": "n"}
        items = [good, dict(good, url="https://www.bls.gov/y", source_domain="evil.com"),
                 dict(good, url="https://www.bls.gov/z", date="2026-10-01"),
                 dict(good, url="https://www.bls.gov/f", date="2026-11-20"),
                 dict(good, url=""), dict(good), dict(good, url="https://www.cnbc.com/a", source_domain="cnbc.com", direction="up")]
        acc, rej = news.ingest(items, d, today)
        assert len(acc) == 1 and len(rej) == 6, (len(acc), [r for _, r in rej])
        reasons = " | ".join(r for _, r in rej)
        for k in ("allowlist", "older", "future", "missing url", "duplicate", "direction"):
            assert k in reasons, k
        assert os.path.exists(os.path.join(d, "news", "accepted", "2026-11-13.json"))
        assert os.path.exists(os.path.join(d, "news", "rejections.csv"))
    finally:
        shutil.rmtree(d)
    print("  news validation rules OK")


def test_targets_basic():
    g = pd.Series([100.0, 90, 95, 80, 120] + [100.0] * 300, index=pd.bdate_range("2000-01-03", periods=305))
    D = targets.daily_forward(g)
    assert abs(D["fwd_min_21"].iloc[0] - (-0.2)) < 1e-12 and abs(D["fwd_ret_21"].iloc[0] - 0.0) < 1e-12
    print("  targets arithmetic OK")


def test_zone_arithmetic_and_history():
    # 100 -> 200 (record) -> 150 (-25%) -> 100 (-50%, low) -> 210 (new record); later 210 -> 180 (-14%) open episode
    px = [100.0, 200.0, 150.0, 120.0, 100.0, 130.0, 210.0, 190.0, 180.0]
    s = pd.Series(px, index=pd.bdate_range("2020-01-01", periods=len(px)))
    a = {"ticker": "T", "name": "t", "asset_class": "x", "currency": "USD", "use_adjclose": False,
         "zones": (10, 20, 30, 40), "note": ""}
    r = assets.compute_asset(a, s)
    assert r["record_close"] == 210.0 and abs(r["pct_below_record"] - (1 - 180 / 210) * 100) < 1e-9
    assert abs(r["zone_prices"][10] - 189.0) < 1e-9 and abs(r["zone_prices"][40] - 126.0) < 1e-9
    assert abs(r["zone_distance_pct"][10] - (180 / 189 - 1) * 100) < 1e-9
    assert r["deepest_zone"] == 10, r["deepest_zone"]
    zh = r["zone_history"]
    # zone 10: first episode (peak 200) crossed at 150; second (peak 210) crossed at 180 and is still open
    assert zh[10]["n_episodes"] == 2 and zh[10]["n_open"] == 1 and zh[10]["n_completed"] == 1
    # zone 40 (level 120) crossed only in the first episode, at 120; low 100 one bar later
    assert zh[40]["n_episodes"] == 1 and abs(zh[40]["further_fall_median"] - (100 / 120 - 1)) < 1e-12
    assert zh[40]["days_to_low_median"] == 1
    # zone 20: first close <= 160 is 150, low 100 -> further fall -1/3, 2 bars later
    assert abs(zh[20]["further_fall_median"] - (100 / 150 - 1)) < 1e-12 and zh[20]["days_to_low_median"] == 2
    # no 252-day history after the cross: forward stats are empty, not invented
    assert zh[20]["fwd_1y_n"] == 0 and zh[20]["fwd_1y_median"] is None
    print("  zone prices, distances, episode stats OK")


def test_zone_flags_enter_exit():
    d = tempfile.mkdtemp()
    try:
        def row(t, z):
            return {"ticker": t, "name": t, "deepest_zone": z}
        r1 = [row("A", 0), row("B", 20)]
        ch, _ = assets.flag_changes(r1, "2026-01-02", d)
        assert ch == [] and all(r["flag"] == "" for r in r1)
        r2 = [row("A", 10), row("B", 10)]
        ch, prev = assets.flag_changes(r2, "2026-01-09", d)
        assert [r["flag"] for r in r2] == ["ENTERED", "EXITED"] and prev == "2026-01-02"
        r3 = [row("A", 10), row("B", 10)]            # same as-of date again: same flags, state not rolled
        ch, _ = assets.flag_changes(r3, "2026-01-09", d)
        assert [r["flag"] for r in r3] == ["ENTERED", "EXITED"]
    finally:
        shutil.rmtree(d)
    print("  ENTERED / EXITED flags OK")


def test_parsers_and_cape_flag():
    import io, json
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    ws.append(["Year-Month", "Debit", "Free cash", "Free margin"])
    ws.append(["2026-10", 1448360, 210290, 212890]); ws.append(["2026-09", 1480054, 215328, 218581])
    buf = io.BytesIO(); wb.save(buf)
    f = data.parse_finra(buf.getvalue())
    assert list(f["debit"]) == [1480054, 1448360] and str(f["date"].iloc[-1].date()) == "2026-10-01"
    j = json.dumps({"observations": [{"d": "2026-11-11", "V1": {"v": "2.50"}}, {"d": "2026-11-12", "V1": {"v": ""}},
                                     {"d": "2026-11-10", "V1": {"v": "2.25"}}]}).encode()
    b = data.parse_boc(j, "V1")
    assert list(b["value"]) == [2.25, 2.5] and len(b) == 2
    # CAPE is flagged as an estimate when the lagged E10 month is past the last reported-earnings month
    r = raw()
    F, _, info = features.build(r)
    sh = r["shiller"]
    if "Earnings" in sh.columns and r["shiller_source"] == "official":
        last_e = sh["Earnings"].dropna().index[-1].to_period("M")
        assert bool(F["cape_is_estimate"].iloc[-1]) == bool(F.index[-1] - 3 > last_e)
        assert not F["cape_is_estimate"].loc[:last_e].any()
    print("  FINRA/BoC parsers and cape_is_estimate flag OK")


def test_signal_board_no_lookahead_and_stats():
    r = raw()
    F, g, _ = features.build(r)
    S, V = signals.board_series(F, r)
    assert list(S.columns) == [b[0] for b in signals.BOARD]
    for cutoff in ("1999-12-31", "2015-12-31"):
        rt = features.truncate_raw(r, cutoff)
        Ft, _, _ = features.build(rt)
        St, _ = signals.board_series(Ft, rt)
        cut = pd.Period(cutoff, "M")
        pd.testing.assert_frame_equal(S.loc[:cut], St.loc[:cut], check_exact=False, rtol=1e-9, atol=1e-12)
    T = targets.month_targets(F, g)
    b = signals.tested_board(F, T, g, r, episodes.episodes(g, F))
    rows = {x["signal"]: x for x in b["signals"]}
    assert len(rows) == 15 and b["n_base"] == 13
    for x in rows.values():
        for k in ("hit_rate_12m", "base_rate_12m", "false_alarm_24m", "bears_caught_rate"):
            assert x[k] is None or 0 <= x[k] <= 1
        assert x["bears_caught"] <= x["bears_eligible"] and x["state"] in ("ON", "OFF", "n/a")
    # base rate of the 12m event over all complete months equals the mean of the target
    done = ~F["partial_month"]
    m = done & T["dd20_12m"].notna() & S["cape30"].notna()
    assert abs(rows["cape30"]["base_rate_12m"] - T["dd20_12m"][m].mean()) < 1e-12
    assert rows["count_ge4"]["state"] == ("ON" if b["base_on"] >= 4 else "OFF")
    print(f"  board: {b['base_on']} of 13 ON, no look-ahead through 1999/2015")


def test_asset_predictions_no_lookahead_and_ledger():
    s = raw()["yahoo"]["NVDA"].dropna()
    f = assetpred.backtest_series(s, "dd10_3m")
    for k in (500, 2000, len(f) - 1):
        row = f.iloc[k]
        t = s.index.get_loc(row["date"])
        p = assetpred.predict_one(s.values[: t + 1], "dd10_3m")        # only data up to t
        assert abs(p["base"] - row["base"]) < 1e-12 and abs(p["cond"] - row["cond"]) < 1e-12, (k, p, row.to_dict())
        # outcome used for scoring is the one after t, never part of the estimate
        fut = s.values[t + 1: t + 64]
        assert (fut.min() / s.values[t] - 1 <= -0.10 + 1e-12) == bool(row["y"])
    # a series shorter than 10 years is not eligible
    assert not assetpred.eligible(s[s.index > s.index[-1] - pd.DateOffset(years=9)])
    assert assetpred.eligible(s)
    # ledger: asset ids chain, are idempotent, resolve against the asset series, and move the shared weight
    d = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(d, "config"))
        shutil.copy(os.path.join(ROOT, "config", "assets.csv"), os.path.join(d, "config", "assets.csv"))
        g = _synthetic_g()
        asofs = [str(g.index[i].date()) for i in range(0, 40)]
        outs = [ledger.outcome_for(g, a, "dd10_3m") for a in asofs]
        assert all(o is not None for o in outs)
        mk = lambda a, o: _pred(a, q="dd10_3m@FAKE", h=63, p=0.9 if o == 1 else 0.1)
        assert ledger.issue([mk(a, o) for a, o in zip(asofs, outs)], d) == 40
        assert ledger.issue([mk(a, o) for a, o in zip(asofs, outs)], d) == 0
        assert ledger.resolve(g, d) == 0, "asset predictions need their own series"
        assert ledger.resolve(g, d, series_for=lambda t: g if t == "FAKE" else None) == 40
        assert ledger.verify(d)[0]
        selfcorrect.save_weights({"asset_dd10_3m": 0.5, "dd10_3m": 0.5}, d)
        ch = selfcorrect.run(d)
        assert [c[1] for c in ch] == ["asset_dd10_3m"] and abs(selfcorrect.load_weights(d)["asset_dd10_3m"] - 0.55) < 1e-9
        assert selfcorrect.load_weights(d)["dd10_3m"] == 0.5, "S&P weight untouched by asset predictions"
        acc = {(a["question"], a["asset_class"]): a for a in assetpred.accuracy(d)}
        # FAKE is not in the universe -> class 'unknown'
        assert acc[("dd10_3m", "unknown")]["n_resolved"] == 40 and acc[("dd10_3m", "unknown")]["skill"] > 0
    finally:
        shutil.rmtree(d)
    print("  asset predictions: no look-ahead, eligibility, ledger, resolution, shared weight OK")


def test_news_cannot_change_numbers():
    r = raw()
    last = r["yahoo"]["^GSPC"].index[-1].date()
    outs = []
    for with_news in (False, True):
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, "data"))
            os.symlink(os.path.join(ROOT, "data", "raw"), os.path.join(d, "data", "raw"))
            shutil.copytree(os.path.join(ROOT, "config"), os.path.join(d, "config"))
            if with_news:
                items = [{"date": str(date.today()), "url": "https://www.bls.gov/x", "source_domain": "bls.gov",
                          "headline": "Everything is on fire", "tag": "crash", "direction": "risk_up", "note": "n"}]
                acc, _ = news.ingest(items, d)
                assert len(acc) == 1
            L = runmod.weekly(d, refresh=False, quiet=True, today=last)
            L = json.load(open(os.path.join(d, "state", "latest.json")))
            preds = [{k: v for k, v in p.items() if k not in ("issued_at_utc", "prev_hash", "row_hash")}
                     for p in ledger.read_predictions(d)]
            outs.append((L, preds, json.load(open(os.path.join(d, "state", "alerts.json")))))
        finally:
            shutil.rmtree(d)
    (a, pa, aa), (b, pb, ab) = outs
    assert a["news"] == [] and len(b["news"]) == 1, "news must reach the report only as text"
    for L in (a, b):
        for k in ("news", "generated_at_utc", "runtime_seconds"):
            L.pop(k)
    assert a == b, "news changed a number in state/latest.json"
    assert pa == pb and aa == ab, "news changed predictions or alerts"
    print("  news item changes nothing in latest.json, ledger probabilities or alerts")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fails = 0
    for t in tests:
        try:
            print(f"{t.__name__} ...")
            t()
            print("  PASS")
        except Exception:
            fails += 1
            print("  FAIL")
            traceback.print_exc()
    print(f"\n{len(tests) - fails}/{len(tests)} tests passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
