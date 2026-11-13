"""Month-end feature table, 1881 -> latest, built with no look-ahead.

Conventions (all documented in README):
  * infl_yoy, rate10, bill3m, curve, credit_spread and their changes are in percent / percentage points.
  * mom_12m, trend_10m, dd_now, rv_3m are fractions.
  * Shiller CPI is lagged 1 month, Shiller earnings-based E10 is lagged 3 months.
"""
import numpy as np
import pandas as pd

FEATURE_COLS = ["cape", "cape_pct", "infl_yoy", "infl_chg_12m", "rate10", "rate10_chg_12m", "ecy",
                "mom_12m", "trend_10m", "dd_now", "rv_3m", "curve", "bill_chg_12m", "credit_spread",
                "credit_spread_chg_12m", "unemp_gap"]
ANALOG_COLS = ["cape_pct", "infl_yoy", "infl_chg_12m", "rate10_chg_12m", "mom_12m", "trend_10m", "rv_3m",
               "dd_now"]


def truncate_raw(raw, cutoff):
    """Return a copy of raw inputs containing only data dated <= cutoff (for no-look-ahead tests)."""
    c = pd.Timestamp(cutoff)
    out = {"shiller": raw["shiller"][raw["shiller"].index <= c], "shiller_source": raw.get("shiller_source"),
           "cape_anchor": None,
           "yahoo": {k: (v[v.index <= c] if v is not None else None) for k, v in raw["yahoo"].items()},
           "fred": {k: (v[v.index <= c] if v is not None else None) for k, v in raw["fred"].items()}}
    if "yahoo_adj" in raw:
        out["yahoo_adj"] = {k: (v[v.index <= c] if v is not None else None) for k, v in raw["yahoo_adj"].items()}
    return out


def _per(s):
    s = s.copy()
    s.index = s.index.to_period("M")
    return s[~s.index.duplicated(keep="last")]


def _month_last(daily):
    return daily.groupby(daily.index.to_period("M")).last()


def build(raw):
    """Return (features DataFrame indexed by month Period, daily ^GSPC close Series, info dict)."""
    sh = raw["shiller"].replace(0.0, np.nan)
    g = raw["yahoo"]["^GSPC"].dropna()
    fred = raw["fred"]
    last_per = g.index[-1].to_period("M")
    months = pd.period_range("1881-01", last_per, freq="M")
    shp = sh.copy()
    shp.index = shp.index.to_period("M")

    # ---- price: Yahoo month-end close from 1928-01, Shiller monthly average (ratio-spliced) before
    me_close = _month_last(g)
    me_date = g.index.to_series().groupby(g.index.to_period("M")).last()
    ym = g.groupby(g.index.to_period("M")).mean()
    ov = pd.period_range("1928-01", "1928-12", freq="M")
    ratio = float(np.nanmedian((ym.reindex(ov) / shp["SP500"].reindex(ov)).values))
    price = pd.Series(np.nan, index=months)
    pre = months[months < pd.Period("1928-01", "M")]
    price.loc[pre] = (shp["SP500"].reindex(pre) * ratio).values
    post = months[months >= pd.Period("1928-01", "M")]
    price.loc[post] = me_close.reindex(post).values
    dates = pd.Series(months.to_timestamp(how="end").normalize(), index=months)
    dates.loc[post] = me_date.reindex(post).values

    F = pd.DataFrame(index=months)
    F["date"] = dates
    F["close"] = price
    last_date = g.index[-1]
    month_end = last_per.to_timestamp(how="end").normalize()
    F["partial_month"] = False
    if (month_end - last_date).days > 4:
        F.loc[last_per, "partial_month"] = True

    # ---- CPI: Shiller, extended with FRED CPIAUCSL chained at the last Shiller month
    cpi = shp["Consumer Price Index"].reindex(months)
    lc = cpi.last_valid_index()
    fc = fred.get("CPIAUCSL")
    cpi_src_last = lc
    if fc is not None and len(fc):
        fp = _per(fc).reindex(months)
        if lc is not None and not np.isnan(fp.get(lc, np.nan)):
            scale = cpi[lc] / fp[lc]
            ext = (fp * scale)
            cpi = cpi.where(cpi.index <= lc, ext)
    # a single unpublished month inside the series (e.g. 2025-10, no BLS release) is log-interpolated
    miss = cpi.isna() & cpi.shift(1).notna() & cpi.shift(-1).notna()
    cpi = np.exp(np.log(cpi).interpolate(limit=1, limit_area="inside"))
    interp = [str(x) for x in cpi.index[miss]]
    F["cpi"] = cpi
    cpi_known = cpi.shift(1)
    F["infl_yoy"] = (cpi_known / cpi_known.shift(12) - 1) * 100
    F["infl_chg_12m"] = F["infl_yoy"] - F["infl_yoy"].shift(12)
    infl10 = (cpi_known / cpi_known.shift(120)) ** (1 / 10) - 1

    # ---- CAPE: Shiller PE10 rescaled to month-end close; E10 lagged 3 months
    pe = shp["PE10"].reindex(months)
    e = shp["SP500"].reindex(months) / (cpi * pe)          # nominal E10 per CPI unit
    le = e.last_valid_index()
    anchor = raw.get("cape_anchor")
    anchor_used = False
    if anchor and anchor.get("e_per_cpi"):
        am = pd.Period(anchor["month"], "M")
        if (le is None or am > le) and am in e.index:
            e.loc[am] = float(anchor["e_per_cpi"])          # official E10 saved on an earlier successful run
            anchor_used = True
    e_ff = e.ffill()
    e_last = e.dropna()
    e_lag = e_ff.shift(3)
    F["cape"] = F["close"] / cpi_known / e_lag
    est = pd.Series(np.arange(len(months)), index=months)
    F["cape_is_estimate"] = (est - 3) > (est[le] if le is not None else -1)   # le = last *official* PE10 month
    c = F["cape"].values
    pct = np.full(len(c), np.nan)
    for i in range(len(c)):
        if not np.isnan(c[i]):
            h = c[: i + 1]
            h = h[~np.isnan(h)]
            pct[i] = (h <= c[i]).sum() / len(h)
    F["cape_pct"] = pct

    # ---- rates
    tnx = _month_last(raw["yahoo"]["^TNX"].dropna()) if raw["yahoo"].get("^TNX") is not None else None
    r10 = shp["Long Interest Rate"].reindex(months)
    if tnx is not None:
        t = tnx.reindex(months)
        r10 = t.where(t.notna(), r10)
    F["rate10"] = r10
    F["rate10_chg_12m"] = r10 - r10.shift(12)
    F["ecy"] = 1.0 / F["cape"] - (r10 / 100 - infl10)

    bill = pd.Series(np.nan, index=months)
    if fred.get("TB3MS") is not None:
        bill = _per(fred["TB3MS"]).reindex(months)
    if raw["yahoo"].get("^IRX") is not None:
        irx = _month_last(raw["yahoo"]["^IRX"].dropna()).reindex(months)
        bill = irx.where(irx.notna(), bill)
    F["bill3m"] = bill
    F["curve"] = r10 - bill
    F["bill_chg_12m"] = bill - bill.shift(12)

    # ---- momentum / trend / drawdown / vol
    mom = F["close"] / F["close"].shift(12) - 1
    if F["partial_month"].iloc[-1]:
        ref = last_date - pd.DateOffset(years=1)
        gl = g[g.index <= ref]
        if len(gl):
            mom.iloc[-1] = g.iloc[-1] / gl.iloc[-1] - 1
    F["mom_12m"] = mom
    F["trend_10m"] = F["close"] / F["close"].rolling(10).mean() - 1
    pre_max = F["close"].where(F.index < pd.Period("1928-01", "M")).cummax()
    dmax = g.cummax()
    dm = dmax.groupby(dmax.index.to_period("M")).last()
    runmax = pd.concat([pre_max.ffill(), dm.reindex(months)], axis=1).max(axis=1)
    # daily running max at the month-end date equals last cummax of that month
    F["dd_now"] = F["close"] / runmax - 1
    rv = g.pct_change().rolling(63).std() * np.sqrt(252)
    F["rv_3m"] = _month_last(rv.dropna()).reindex(months)

    # ---- FRED-dependent: credit, unemployment
    cs = pd.Series(np.nan, index=months)
    if fred.get("BAA") is not None and fred.get("AAA") is not None:
        cs = (_per(fred["BAA"]) - _per(fred["AAA"])).reindex(months).ffill(limit=2)
    F["credit_spread"] = cs
    F["credit_spread_chg_12m"] = cs - cs.shift(12)
    ug = pd.Series(np.nan, index=months)
    if fred.get("UNRATE") is not None:
        u = _per(fred["UNRATE"]).reindex(months).shift(1)   # published early next month
        ug = u - u.rolling(12, min_periods=10).min()
    F["unemp_gap"] = ug
    F["div"] = shp["Dividend"].reindex(months)

    info = {"price_splice_ratio": ratio, "last_valid_pe10": str(le), "last_shiller_cpi": str(cpi_src_last),
            "fred_cpi_used": bool(fc is not None and len(fc)), "cpi_interpolated_months": interp,
            "shiller_source": raw.get("shiller_source"), "anchor_used": anchor_used,
            "e_per_cpi_last": float(e_last.iloc[-1]) if len(e_last) else None,
            "e_last_month": str(e_last.index[-1]) if len(e_last) else None}
    cols = ["date", "close", "partial_month", "cape_is_estimate"] + FEATURE_COLS + ["bill3m", "cpi", "div"]
    return F[cols], g, info


def percentile_ranks(F, row):
    out = {}
    for c in FEATURE_COLS:
        v = row.get(c)
        s = F[c].dropna()
        out[c] = None if v is None or pd.isna(v) or not len(s) else float((s <= v).mean())
    return out
