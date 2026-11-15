"""Rules board: each rule's current value, ON/OFF and its own history vs. P(dd20_12m)."""
import numpy as np
import pandas as pd

RULES = [
    ("valuation", "vulnerability", "CAPE percentile >= 0.90"),
    ("tightening", "vulnerability", "3m bill 12m change > +0.25 pt, or 10y yield 12m change > +0.5 pt"),
    ("inflation_reaccelerating", "vulnerability", "CPI yoy > 3% and its 12m change > +0.5 pt"),
    ("oil_shock", "vulnerability", "Brent 12m change >= +40%"),
    ("leader_crack", "vulnerability", "NVDA >= 20% below 52w high while S&P within 10% of its 52w high (current only)"),
    ("narrow_market", "vulnerability", "RSP 12m return minus SPY 12m return <= -5 pt"),
    ("trend_break", "trigger", "S&P close below its 10-month average"),
    ("credit_stress", "trigger", "HYG >= 7% below 52w high, or HY OAS > 5% (FRED)"),
    ("volatility_regime", "trigger", "VIX > 30 at month end"),
    ("curve_inverted", "trigger", "10y yield minus 3m bill < 0"),
]


def _asof(s, d):
    """Last value of series s at or before date d (NaN if none)."""
    i = s.index.searchsorted(d, side="right") - 1
    return s.iloc[i] if i >= 0 else np.nan


def _asof_many(s, dates):
    idx = s.index.searchsorted(pd.DatetimeIndex(dates), side="right") - 1
    v = np.where(idx >= 0, s.values[np.clip(idx, 0, None)], np.nan)
    # series must actually start before the date
    return v


def _chg12(s, dates):
    """12m percent change using last obs <= date and <= date-12m; NaN if the series does not reach back."""
    dates = pd.DatetimeIndex(dates)
    now = _asof_many(s, dates)
    ref_dates = dates - pd.DateOffset(years=1)
    ref = _asof_many(s, ref_dates)
    ok = ref_dates >= s.index[0]
    return np.where(ok, now / ref - 1, np.nan)


def _high52_dd(s, dates):
    out = []
    for d in pd.DatetimeIndex(dates):
        w = s[(s.index > d - pd.Timedelta(days=365)) & (s.index <= d)]
        full = len(s) and s.index[0] <= d - pd.Timedelta(days=330)
        out.append(w.iloc[-1] / w.max() - 1 if len(w) and full else np.nan)
    return np.array(out)


def _tf(cond, valid):
    return pd.Series(np.where(valid, cond.astype(float), np.nan))


def rule_series(F, raw):
    dates = pd.DatetimeIndex(F["date"])
    S = pd.DataFrame(index=F.index)
    V = pd.DataFrame(index=F.index)      # numeric value of each rule's main input
    S["valuation"] = np.where(F["cape_pct"].isna(), np.nan, (F["cape_pct"] >= 0.90).astype(float))
    V["valuation"] = F["cape_pct"]
    a, b = F["bill_chg_12m"], F["rate10_chg_12m"]
    t_on = (a > 0.25) | (b > 0.5)                       # NaN comparisons are False
    S["tightening"] = np.where(a.isna() & b.isna(), np.nan, t_on.astype(float))
    V["tightening"] = a.where(a.notna(), b)
    ii = (F["infl_yoy"] > 3) & (F["infl_chg_12m"] > 0.5)
    S["inflation_reaccelerating"] = np.where(F["infl_yoy"].isna() | F["infl_chg_12m"].isna(), np.nan, ii.astype(float))
    V["inflation_reaccelerating"] = F["infl_yoy"]
    brent = raw["yahoo"].get("BZ=F")
    if brent is not None:
        ch = _chg12(brent.dropna(), dates)
        S["oil_shock"] = np.where(np.isnan(ch), np.nan, (ch >= 0.40).astype(float))
        V["oil_shock"] = ch
    else:
        S["oil_shock"] = np.nan
        V["oil_shock"] = np.nan
    S["leader_crack"] = np.nan
    V["leader_crack"] = np.nan
    rsp, spy = raw["yahoo_adj"].get("RSP"), raw["yahoo_adj"].get("SPY")
    if rsp is not None and spy is not None:
        diff = _chg12(rsp.dropna(), dates) - _chg12(spy.dropna(), dates)
        S["narrow_market"] = np.where(np.isnan(diff), np.nan, (diff <= -0.05).astype(float))
        V["narrow_market"] = diff
    else:
        S["narrow_market"] = np.nan
        V["narrow_market"] = np.nan
    S["trend_break"] = np.where(F["trend_10m"].isna(), np.nan, (F["trend_10m"] < 0).astype(float))
    V["trend_break"] = F["trend_10m"]
    hyg = raw["yahoo_adj"].get("HYG")
    hy = raw["fred"].get("BAMLH0A0HYM2")
    c1 = np.full(len(F), np.nan)
    c2 = np.full(len(F), np.nan)
    dd = np.full(len(F), np.nan)
    if hyg is not None:
        dd = _high52_dd(hyg.dropna(), dates)
        c1 = np.where(np.isnan(dd), np.nan, (dd <= -0.07).astype(float))
    if hy is not None:
        h = _asof_many(hy.dropna(), dates)
        okd = dates >= hy.dropna().index[0]
        h = np.where(okd, h, np.nan)
        c2 = np.where(np.isnan(h), np.nan, (h > 5.0).astype(float))
    anyon = (np.nan_to_num(c1, nan=0) + np.nan_to_num(c2, nan=0)) > 0
    avail = ~(np.isnan(c1) & np.isnan(c2))
    S["credit_stress"] = np.where(avail, anyon.astype(float), np.nan)
    V["credit_stress"] = dd
    vix = raw["yahoo"].get("^VIX")
    if vix is not None:
        v = _asof_many(vix.dropna(), dates)
        v = np.where(dates >= vix.dropna().index[0], v, np.nan)
        S["volatility_regime"] = np.where(np.isnan(v), np.nan, (v > 30).astype(float))
        V["volatility_regime"] = v
    else:
        S["volatility_regime"] = np.nan
        V["volatility_regime"] = np.nan
    S["curve_inverted"] = np.where(F["curve"].isna(), np.nan, (F["curve"] < 0).astype(float))
    V["curve_inverted"] = F["curve"]
    return S, V


def _leader_crack_now(raw, asof):
    nv = raw["yahoo"].get("NVDA")
    g = raw["yahoo"].get("^GSPC")
    if nv is None or g is None:
        return None, None, None
    d_n = _high52_dd(nv.dropna(), [asof])[0]
    d_s = _high52_dd(g.dropna(), [asof])[0]
    if np.isnan(d_n) or np.isnan(d_s):
        return None, None, None
    return bool(d_n <= -0.20 and d_s >= -0.10), float(d_n), float(d_s)


def _runs(x):
    n, prev = 0, 0.0
    for v in x:
        if v == 1.0 and prev != 1.0:
            n += 1
        prev = v
    return n


def board(F, T, raw):
    S, V = rule_series(F, raw)
    y = T["dd20_12m"]
    asof = pd.Timestamp(F["date"].iloc[-1])
    rows = []
    for name, kind, desc in RULES:
        s = S[name]
        cur_val = V[name].iloc[-1] if name in V else np.nan
        cur_on = s.iloc[-1]
        extra = {}
        if name == "leader_crack":
            on, dn, ds = _leader_crack_now(raw, asof)
            cur_on = np.nan if on is None else float(on)
            cur_val = dn
            extra = {"nvda_vs_52w_high": dn, "sp500_vs_52w_high": ds}
        valid = s.notna()
        resolved = valid & y.notna()
        on_m = resolved & (s == 1)
        off_m = resolved & (s == 0)
        rec = {
            "rule": name, "type": kind, "definition": desc,
            "current_value": None if cur_val is None or pd.isna(cur_val) else float(cur_val),
            "state": "ON" if cur_on == 1 else ("OFF" if cur_on == 0 else "n/a"),
            "history_first_month": str(s[valid].index[0]) if valid.any() else None,
            "months_with_input": int(valid.sum()),
            "months_on": int((s == 1).sum()),
            "on_episodes": _runs(s.fillna(0).values),
            "n_on_resolved": int(on_m.sum()), "n_off_resolved": int(off_m.sum()),
            "p_dd20_12m_given_on": float(y[on_m].mean()) if on_m.sum() else None,
            "p_dd20_12m_given_off": float(y[off_m].mean()) if off_m.sum() else None,
            "p_dd20_12m_all_in_window": float(y[resolved].mean()) if resolved.sum() else None,
        }
        if name == "tightening":
            extra = {"bill_chg_12m": None if pd.isna(F["bill_chg_12m"].iloc[-1]) else float(F["bill_chg_12m"].iloc[-1]),
                     "rate10_chg_12m": None if pd.isna(F["rate10_chg_12m"].iloc[-1]) else float(F["rate10_chg_12m"].iloc[-1])}
        if name == "leader_crack":
            rec["history_note"] = "current only; no history computed"
        rec.update(extra)
        rows.append(rec)
    vuln_on = sum(1 for r in rows if r["type"] == "vulnerability" and r["state"] == "ON")
    trig_on = sum(1 for r in rows if r["type"] == "trigger" and r["state"] == "ON")
    return {"asof": str(asof.date()), "rules": rows, "vulnerability_on": vuln_on, "trigger_on": trig_on}


# ---------------------------------------------------------------------------------------------------------
# Tested signal board: 13 base signals + combo + count, each backtested against S&P 500 bear markets.
# Monthly grid = the feature table's month-ends. Every threshold is fixed here; every statistic is computed at
# run time from downloaded data. A signal value at month t uses only data published by the end of month t
# (CPI/UNRATE lagged one month and Shiller E10 lagged three months inside features.py, FINRA lagged one month).

BOARD = [  # name, label, definition
    ("cape30", "CAPE above 30", "Shiller CAPE (month-end price, lagged E10) > 30"),
    ("cape90", "CAPE in its top 10%", "CAPE above its own expanding 90th percentile (history from 1881, min 10 years)"),
    ("curve_inv", "Yield curve inverted", "10-year yield minus 3-month bill < 0"),
    ("fed_tight", "Fed tightening", "3-month bill up >= 1.5 points over 12 months"),
    ("infl", "Inflation above 4% and rising", "CPI year-on-year > 4% and above its level 12 months earlier"),
    ("credit_baa_aaa", "BAA-AAA spread widening", "Moody's BAA minus AAA yield up >= 0.3 points over 6 months"),
    ("hy_oas", "High-yield spread (OAS)", "ICE BofA HY OAS > 5% and up >= 1.5 points over 3 months (FRED serves ~3 years only)"),
    ("trend_break", "S&P below 10-month average", "S&P 500 month-end close below its 10-month average"),
    ("sahm", "Sahm-style unemployment rise", "Unemployment rate >= 0.5 points above its trailing 12-month low"),
    ("oil_up50", "Oil up 50%", "WTI monthly average up >= 50% over 12 months"),
    ("narrow", "Narrow market", "Equal-weight (RSP) 12m return minus cap-weight (SPY) <= -5 points (adjusted prices)"),
    ("margin_yoy30", "Margin debt up 30%", "FINRA margin debt up > 30% year on year (lagged one month)"),
    ("vix30", "VIX above 30", "VIX month-end close > 30"),
    ("combo_cape90_trend", "CAPE top 10% and trend broken", "cape90 and trend_break both ON"),
    ("count_ge4", "4 or more base signals ON", "At least 4 of the 13 base signals ON (no-data counts as OFF)"),
]
BASE = [b[0] for b in BOARD[:13]]


def _monthly(s, idx, how="last"):
    """Daily/monthly Series -> value per Period in idx (last observation of the month)."""
    s = s.dropna()
    if s.empty:
        return pd.Series(np.nan, index=idx)
    p = s.groupby(s.index.to_period("M")).last()
    return p.reindex(idx)


def board_series(F, raw):
    """Return (S, V): S = 1/0/NaN signal table, V = numeric reading per signal, both indexed like F."""
    idx = F.index
    S, V = pd.DataFrame(index=idx), pd.DataFrame(index=idx)

    def put(name, cond, val, ok):
        S[name] = np.where(ok, cond.astype(float), np.nan)
        V[name] = val

    cape = F["cape"]
    thr = cape.expanding(min_periods=120).quantile(0.9)
    put("cape30", cape > 30, cape, cape.notna())
    put("cape90", cape > thr, cape - thr, cape.notna() & thr.notna())
    put("curve_inv", F["curve"] < 0, F["curve"], F["curve"].notna())
    put("fed_tight", F["bill_chg_12m"] >= 1.5, F["bill_chg_12m"], F["bill_chg_12m"].notna())
    y, y0 = F["infl_yoy"], F["infl_yoy"].shift(12)
    put("infl", (y > 4) & (y > y0), y, y.notna() & y0.notna())
    c6 = F["credit_spread"] - F["credit_spread"].shift(6)
    put("credit_baa_aaa", c6 >= 0.3, c6, c6.notna())
    hy = raw["fred"].get("BAMLH0A0HYM2")
    hym = _monthly(hy, idx) if hy is not None else pd.Series(np.nan, index=idx)
    h3 = hym - hym.shift(3)
    put("hy_oas", (hym > 5) & (h3 >= 1.5), hym, hym.notna() & h3.notna())
    put("trend_break", F["trend_10m"] < 0, F["trend_10m"], F["trend_10m"].notna())
    ug = F["unemp_gap"]
    put("sahm", ug >= 0.5, ug, ug.notna())
    wti = raw["fred"].get("WTISPLC")
    wm = _monthly(wti, idx) if wti is not None else pd.Series(np.nan, index=idx)
    o12 = wm / wm.shift(12) - 1
    put("oil_up50", o12 >= 0.5, o12, o12.notna())
    rsp, spy = raw["yahoo_adj"].get("RSP"), raw["yahoo_adj"].get("SPY")
    if rsp is not None and spy is not None:
        r, s_ = _monthly(rsp, idx), _monthly(spy, idx)
        nr = (r / r.shift(12)) - (s_ / s_.shift(12))
    else:
        nr = pd.Series(np.nan, index=idx)
    put("narrow", nr <= -0.05, nr, nr.notna())
    fin = raw.get("finra")
    if fin is not None:
        f = fin.copy()
        f.index = f.index.to_period("M")
        f = f.shift(1).reindex(idx)               # published ~3 weeks after month end: use last month's figure
    else:
        f = pd.Series(np.nan, index=idx)
    mg = f / f.shift(12) - 1
    put("margin_yoy30", mg > 0.30, mg, mg.notna())
    vix = raw["yahoo"].get("^VIX")
    vm = _monthly(vix, idx) if vix is not None else pd.Series(np.nan, index=idx)
    put("vix30", vm > 30, vm, vm.notna())
    both = S["cape90"].notna() & S["trend_break"].notna()
    put("combo_cape90_trend", (S["cape90"] == 1) & (S["trend_break"] == 1), np.nan, both)
    V["combo_cape90_trend"] = np.where(both, S["combo_cape90_trend"], np.nan)
    cnt = S[BASE].fillna(0).sum(axis=1)
    put("count_ge4", cnt >= 4, cnt, pd.Series(True, index=idx))
    return S, V


def _bear_windows(eps):
    return [(pd.Timestamp(e["peak_date"]), pd.Timestamp(e["trough_date"]), e["depth"]) for e in eps]


def tested_board(F, T, g, raw, eps):
    """Backtest and today's state for every board signal. eps: output of episodes.episodes (>=20% bears)."""
    S, V = board_series(F, raw)
    complete = ~F["partial_month"].values
    dates = pd.DatetimeIndex(F["date"])
    e12 = T["dd20_12m"].copy()
    c = g.values.astype(float)
    pos = T["idx"].values
    e24 = np.full(len(F), np.nan)
    if len(c) > 505:
        mn = np.full(len(c), np.nan)
        mn[: len(c) - 504] = np.lib.stride_tricks.sliding_window_view(c, 505).min(axis=1) / c[: len(c) - 504] - 1
        ok = pos >= 0
        e24[ok] = mn[pos[ok]]
        e24 = np.where(np.isnan(e24), np.nan, (e24 <= -0.2 + 1e-12).astype(float))
    e24 = pd.Series(e24, index=F.index)
    bears = _bear_windows(eps)
    asof = pd.Timestamp(F["date"].iloc[-1])
    rows = []
    for name, label, desc in BOARD:
        v = S[name].where(pd.Series(complete, index=F.index))
        dv = v.dropna()
        on = v == 1
        r = {"signal": name, "label": label, "definition": desc,
             "first_month": str(dv.index[0]) if len(dv) else None, "months_defined": int(len(dv)),
             "months_on": int(on.sum())}
        for h, e in ((12, e12), (24, e24)):
            m = on & e.notna()
            el = v.notna() & e.notna()
            r[f"n_on_{h}m"] = int(m.sum())
            r[f"hit_rate_{h}m"] = float(e[m].mean()) if m.sum() else None
            r[f"base_rate_{h}m"] = float(e[el].mean()) if el.sum() else None
        r["false_alarm_24m"] = None if r["hit_rate_24m"] is None else 1 - r["hit_rate_24m"]
        elig = caught = 0
        leads = []
        for pk, lo, dep in bears:
            if not len(dv) or pk.to_period("M") < dv.index[0]:
                continue
            elig += 1
            w = (dates <= pk) & (dates > pk - pd.DateOffset(months=12)) & on.values
            if w.any():
                caught += 1
                leads.append((pk - dates[w][0]).days / 30.44)
        r["bears_eligible"], r["bears_caught"] = elig, caught
        r["bears_caught_rate"] = caught / elig if elig else None
        r["median_lead_months"] = float(np.median(leads)) if leads else None
        # today: last row, else the latest of the previous 2 months (monthly sources publish with a delay)
        st, val, dd = np.nan, np.nan, None
        for k in (1, 2, 3):
            if len(S) >= k and not np.isnan(S[name].iloc[-k]):
                st, val, dd = S[name].iloc[-k], V[name].iloc[-k], str(S.index[-k])
                break
        r["state"] = "n/a" if np.isnan(st) else ("ON" if st == 1 else "OFF")
        r["value"] = None if val is None or pd.isna(val) else float(val)
        r["data_month"] = dd
        rows.append(r)
    st = {r["signal"]: r["state"] for r in rows}
    # today's combo and count use each signal's latest available reading (monthly sources publish late)
    by = {r["signal"]: r for r in rows}
    n_on = sum(1 for b in BASE if st[b] == "ON")
    if "n/a" not in (st["cape90"], st["trend_break"]):
        by["combo_cape90_trend"]["state"] = "ON" if st["cape90"] == "ON" and st["trend_break"] == "ON" else "OFF"
        st["combo_cape90_trend"] = by["combo_cape90_trend"]["state"]
    by["count_ge4"].update(state="ON" if n_on >= 4 else "OFF", value=float(n_on))
    st["count_ge4"] = by["count_ge4"]["state"]
    return {"asof": str(asof.date()), "signals": rows, "base_on": n_on,
            "n_base": len(BASE), "bears_in_sample": len(bears),
            "alarm_trend_and_cape90": st["combo_cape90_trend"],
            "event_definition": "S&P 500 daily close falls >= 20% below the month-end close within 12 (24) months"}
