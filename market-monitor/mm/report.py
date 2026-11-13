"""Render REPORT.md from state/latest.json only (no other inputs)."""


def pct(x, d=1):
    return "n/a" if x is None else f"{x * 100:.{d}f}%"


def num(x, d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def render(L):
    o = []
    a = o.append
    a(f"# Market monitor report (as of {L['asof']})\n")
    a(f"Generated {L['generated_at_utc']} UTC. S&P 500 last close {L['sp500_last_close']:.2f}. "
      f"This is a statistical history check, not investment advice; every probability below is a historical frequency "
      f"adjusted by simple models, and the models have only weak out-of-sample skill (see the skill columns).\n")
    m = L["manifest"]
    a("## Data status\n")
    a(f"{m['n_ok']} of {m['n_ok'] + m['n_failed']} sources downloaded. FRED reachable: {'yes' if m['fred_reachable'] else 'no'}."
      + (f" Failed: {', '.join(m['failed'])}." if m["failed"] else ""))
    fi = L["feature_info"]
    if fi["cape_is_estimate"]:
        a(f"\nCAUTION: the Shiller file's last valid CAPE input is {fi['last_valid_pe10']}. Since then the earnings base is held "
          f"constant (in real terms), so today's CAPE is an estimate and probably reads a little high if real earnings kept growing.")
    if fi.get("cpi_interpolated_months"):
        a(f"\nNote: CPI for {', '.join(fi['cpi_interpolated_months'])} was not published and is log-interpolated.")
    if fi["partial_month"]:
        a(f"\nThe latest feature row is a partial month ({fi['feature_row_month']}) using the last close.")
    a("\n## Where the market stands\n")
    f, r = L["features_today"], L["feature_percentile_ranks"]
    a("| Measure | Value | Percentile of own history |\n|---|---|---|")
    fmt = {"cape": lambda v: num(v, 1), "cape_pct": lambda v: pct(v), "infl_yoy": lambda v: num(v) + "%",
           "infl_chg_12m": lambda v: num(v) + " pt", "rate10": lambda v: num(v) + "%", "rate10_chg_12m": lambda v: num(v) + " pt",
           "ecy": lambda v: pct(v), "mom_12m": pct, "trend_10m": pct, "dd_now": pct, "rv_3m": pct,
           "curve": lambda v: num(v) + " pt", "bill_chg_12m": lambda v: num(v) + " pt",
           "credit_spread": lambda v: num(v) + " pt", "credit_spread_chg_12m": lambda v: num(v) + " pt",
           "unemp_gap": lambda v: num(v) + " pt"}
    for k, v in f.items():
        a(f"| {k} | {'n/a' if v is None else fmt.get(k, num)(v)} | {pct(r.get(k), 0)} |")
    a("\n## Probabilities for the S&P 500\n")
    a("`base` is the historical frequency; `final` blends in the analog and regression models using weight w "
      "(0 = ignore models). Skill is Brier skill versus the base rate (positive = better than just quoting the base rate).\n")
    a("| Question | Base | Analog | Logit | Final | w live | Skill 1950-99 | Skill 2000-now (holdout) |\n|---|---|---|---|---|---|---|---|")
    for q, d in L["questions"].items():
        p = d["probabilities"] or {}
        sk1 = (d["walk_forward_1950_1999"] or {}).get("skill_final")
        sk2 = (d["holdout_2000_latest"] or {}).get("skill_final")
        a(f"| {d['text']} | {pct(p.get('base'))} | {pct(p.get('analog'))} | {pct(p.get('logit'))} | {pct(p.get('final'))} | "
          f"{num(d.get('w_live'))} | {num(sk1, 3)} | {num(sk2, 3)} |")
    a("\n## Closest historical analogs\n")
    a("Months whose valuation, inflation, rates, momentum, trend, volatility and drawdown looked most like today.\n")
    a("| Period | Months | Avg distance | Avg next-12m return | Worst drawdown in next 12m |\n|---|---|---|---|---|")
    for gdict in L["analogs"] or []:
        a(f"| {gdict['first']} to {gdict['last']} | {gdict['n_months']} | {num(gdict['mean_distance'])} | "
          f"{pct(gdict['mean_next_12m_return'])} | {pct(gdict['worst_drawdown_12m'])} |")
    c = L["cape_10y_real_return"]
    if c:
        a("\n## Ten-year outlook from valuation\n")
        a(f"CAPE {num(c['cape_now'], 1)}{' (estimate)' if c['cape_is_estimate'] else ''} implies an annualised real return of about "
          f"{pct(c['estimate_real_ann_10y'])} per year over ten years, with a one-standard-deviation band of "
          f"{pct(c['band_1sd'][0])} to {pct(c['band_1sd'][1])} (regression R-squared {num(c['r2'])}, in-sample, "
          f"{c['n_months']} overlapping months).")
    s = L["signals"]
    a(f"\n## Signals board ({s['vulnerability_on']} vulnerability and {s['trigger_on']} trigger rules ON)\n")
    a("| Rule | Type | State | Current value | Months ON | P(20% drop within 12m) when ON | when OFF | History starts |\n|---|---|---|---|---|---|---|---|")
    for x in s["rules"]:
        a(f"| {x['rule']} | {x['type']} | {x['state']} | {num(x['current_value'], 3)} | {x['months_on']} | "
          f"{pct(x['p_dd20_12m_given_on'])} | {pct(x['p_dd20_12m_given_off'])} | {x['history_first_month'] or 'current only'} |")
    a("\n## Past drawdowns of 19.9% or more (daily closes)\n")
    a("| Peak | Trough | Depth | Days to trough | Recovered | CAPE at peak | Rallies >=10% / >=20% |\n|---|---|---|---|---|---|---|")
    for e in L["episodes"]:
        a(f"| {e['peak_date']} | {e['trough_date']} | {pct(e['depth'])} | {e['days_to_trough']} | "
          f"{e['recovered_date'] or 'not yet'} | {num(e['cape_at_peak'], 1)} | {e['rallies_10pct']} / {e['rallies_20pct']} |")
    a("\n## What followed the first close 20%, 30%, 40% below a peak\n")
    a("| Threshold | Peak | Hit date | 1y | 3y | 5y | Further fall to final low | Days later |\n|---|---|---|---|---|---|---|---|")
    for e in L["after_threshold"]:
        a(f"| {pct(e['threshold'], 0)} | {e['peak_date']} | {e['hit_date']} | {pct(e['fwd_ret_1y'])} | {pct(e['fwd_ret_3y'])} | "
          f"{pct(e['fwd_ret_5y'])} | {pct(e['further_fall_to_final_low'])} | {e['days_to_final_low']} |")
    sc = L["scorecard"]
    a("\n## Live scorecard\n")
    o_ = sc["overall"]
    a(f"{o_['n_issued']} predictions issued, {o_['n_resolved']} resolved, {o_['n_pending']} pending."
      + (f" Live Brier {num(o_['brier_final'], 4)} vs base {num(o_['brier_base'], 4)} (skill {num(o_['skill'], 3)})." if o_["n_resolved"] else
         " Nothing has resolved yet, so there is no live skill estimate."))
    a(f"\nLedger check: {L['ledger']['verify_message']}.")
    a("\n## Market snapshot\n")
    a("| Symbol | Last close | Date | Year to date | From 52-week high (closes) |\n|---|---|---|---|---|")
    for k, v in L["market_snapshot"].items():
        if v.get("last_close") is None:
            a(f"| {k} | n/a | | | |")
        else:
            a(f"| {k} | {v['last_close']:.2f} | {v['date']} | {num(v['ytd_pct'], 1)}% | {num(v['pct_from_52w_high'], 1)}% |")
    a("\n## Accepted news (last 10 days)\n")
    if L["news"]:
        for n in L["news"]:
            a(f"- {n['date']} [{n['direction']}] {n['headline']} ({n['source_domain']}) {n['url']}")
    else:
        a("None accepted.")
    return "\n".join(o) + "\n"
