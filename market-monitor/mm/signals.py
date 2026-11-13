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
