"""Spreadsheet export. `python -m mm.sheets` writes two value-only workbooks into out/:
  Market Monitor MASTER.xlsx  - method, signal definitions, history tables, research notes
  Market Monitor ASOF.xlsx    - this run's signals, probabilities, market data, ledger and scorecard
Everything comes from state/latest.json, the ledger files and config/master_notes.csv."""
import csv
import hashlib
import json
import os
import re
import urllib.request

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter
    HAVE_XLSX = True
except ImportError:          # export_all then writes one CSV per tab instead
    HAVE_XLSX = False

from . import ROOT

RULE_NAMES = {
    "valuation": "Valuation very high",
    "tightening": "Interest rates rising",
    "inflation_reaccelerating": "Inflation picking up again",
    "oil_shock": "Oil price shock",
    "leader_crack": "Market leader falling while the index holds",
    "narrow_market": "Narrow market (few shares leading)",
    "trend_break": "Index below its 10-month average",
    "credit_stress": "Credit stress",
    "volatility_regime": "Fear gauge (VIX) above 30",
    "curve_inverted": "Short-term rates above long-term rates",
}
SYMBOL_NAMES = {
    "^GSPC": "S&P 500", "^IXIC": "Nasdaq Composite", "NVDA": "Nvidia", "GOOG": "Alphabet",
    "XEQT.TO": "XEQT global shares fund (CAD)", "^GSPTSE": "S&P/TSX Composite",
    "CAD=X": "Canadian dollars per US dollar", "^TNX": "US 10-year yield (%)",
    "^IRX": "US 3-month bill yield (%)", "^VIX": "VIX volatility index", "HYG": "High-yield bond fund",
    "BZ=F": "Brent crude ($)", "GC=F": "Gold ($)", "DX-Y.NYB": "US dollar index", "BTC-USD": "Bitcoin ($)",
}


def pct(x, d=1):
    return "" if x is None else f"{100 * x:.{d}f}%"


def num(x, d=2):
    return "" if x is None else round(float(x), d)


def tab(wb, title, header, rows):
    ws = wb.create_sheet(title[:31])
    ws.append(header)
    for r in rows:
        ws.append(["" if v is None else v for v in r])
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.freeze_panes = "A2"
    for i, h in enumerate(header, 1):
        longest = max([len(str(h))] + [len(str(r[i - 1])) for r in rows if i - 1 < len(r)])
        ws.column_dimensions[get_column_letter(i)].width = min(90, max(10, longest + 2))
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    return ws


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def canada_rows():
    """Latest Bank of Canada values and the value about 12 months earlier. Missing data is reported, never guessed."""
    series = {
        "V39079": "Bank of Canada policy rate (%)",
        "BD.CDN.5YR.DQ.YLD": "Canada 5-year bond yield (%)",
        "BD.CDN.10YR.DQ.YLD": "Canada 10-year bond yield (%)",
        "FXUSDCAD": "Canadian dollars per US dollar",
        "V80691335": "Posted 5-year mortgage rate (%)",
    }
    rows = []
    for sid, name in series.items():
        try:
            j = json.loads(_get(f"https://www.bankofcanada.ca/valet/observations/{sid}/json?recent=300"))
            obs = sorted((o["d"], float(o[sid]["v"])) for o in j["observations"] if o.get(sid, {}).get("v") not in (None, ""))
            d, v = obs[-1]
            year_ago = str(int(d[:4]) - 1) + d[4:]
            prev = [x for x in obs if x[0] <= year_ago]
            rows.append([name, v, d, prev[-1][1] if prev else "", "Bank of Canada"])
        except Exception as e:  # noqa: BLE001
            rows.append([name, "unavailable", "", "", f"error: {str(e)[:60]}"])
    return rows


def margin_rows():
    """Latest FINRA margin debt (debit balances, $ millions), 12-month change and the record month."""
    try:
        html = _get("https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics")
        cells = re.findall(r"<td[^>]*>\s*([^<]*?)\s*</td>", html)
        data = []
        for i in range(len(cells) - 1):
            if re.fullmatch(r"[A-Z][a-z]{2}-\d{2}", cells[i]) and re.fullmatch(r"[\d,]+", cells[i + 1]):
                data.append((cells[i], int(cells[i + 1].replace(",", ""))))
        if not data:
            raise ValueError("no monthly rows found")
        month, latest = data[0]
        prior_label = f"{month[:3]}-{int(month[4:]) - 1:02d}"
        prior = dict(data).get(prior_label)
        rec_month, rec = max(data, key=lambda x: x[1])
        change = pct(latest / prior - 1) if prior else ""
        return [["Margin debt ($ millions)", latest, month, prior or "", "FINRA"],
                ["Margin debt, 12-month change", change, month, "", "FINRA"],
                ["Margin debt record ($ millions)", rec, rec_month, "", "FINRA"]]
    except Exception as e:  # noqa: BLE001
        return [["Margin debt ($ millions)", "unavailable", "", "", f"error: {str(e)[:60]}"]]


def read_csv(path):
    if not os.path.exists(path):
        return [], []
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return (rows[0], rows[1:]) if rows else ([], [])


def build_master(d, out_dir):
    wb = Workbook()
    wb.remove(wb.active)
    readme = [
        ["What this is", "A weekly check of stock-market warning signs against about 150 years of history. It gives probabilities for the S&P 500, records each one with a date, later scores it against what happened, and adjusts itself."],
        ["How to read the weekly sheet", "Start with Summary. 'Historical odds' is how often the event happened in the past. 'Model' is the same odds adjusted for today's conditions. If the two are close, today's conditions add little."],
        ["Vulnerability and trigger signs", "Vulnerability signs say the market is fragile (expensive, inflation rising). Trigger signs say a fall may be starting (trend broken, credit stress). Large falls in the past usually came after triggers switched on."],
        ["How it corrects itself", "Each prediction is saved before the outcome is known and cannot be edited afterwards. When it comes due it is scored. If the model has been more accurate than the plain historical odds it gets more weight; if less accurate, less weight. Every change is logged in the Changes tab."],
        ["What it cannot do", "It cannot say when a crash will happen. Tested on data since 2000, its 12-month forecasts were no better than the plain historical odds; its 1- and 3-month forecasts were slightly better. See Model skill."],
        ["Where the numbers come from", "Shiller data (shillerdata.com), Yahoo Finance prices (query1.finance.yahoo.com), Federal Reserve data (fred.stlouisfed.org), Bank of Canada (bankofcanada.ca), FINRA margin statistics (finra.org). Every number is computed by code; none is typed in by hand."],
        ["News", "News items are accepted only from an approved list of official and major financial sources, each with a link. They are shown as evidence and never change the numbers."],
        ["Not advice", "This is a statistical history check, not investment advice."],
        ["Model version and date", f"{d.get('model_version')} as of {d.get('asof')}"],
    ]
    tab(wb, "Read me", ["Topic", "Detail"], readme)
    rules = d["signals"]["rules"]
    tab(wb, "Signals guide",
        ["Sign", "Kind", "Rule", "History starts", "Months switched on", "Chance of a 20% fall within 12 months when ON", "When OFF"],
        [[RULE_NAMES.get(r["rule"], r["rule"]), r["type"], r["definition"], r.get("history_first_month") or "current only",
          r.get("months_on"), pct(r.get("p_dd20_12m_given_on")), pct(r.get("p_dd20_12m_given_off"))] for r in rules])
    tab(wb, "Bear markets",
        ["Peak", "Low", "Fall", "Days to the low", "Old peak regained", "Days peak to recovery", "Valuation (CAPE) at peak", "Rallies of 10%+ on the way down", "Rallies of 20%+"],
        [[e["peak_date"], e["trough_date"], pct(e["depth"]), e["days_to_trough"], e.get("recovered_date") or "not yet",
          e.get("days_peak_to_recover"), num(e.get("cape_at_peak"), 1), e.get("rallies_10pct"), e.get("rallies_20pct")] for e in d["episodes"]])
    tab(wb, "After a fall",
        ["First close this far below the peak", "Peak", "Date reached", "1 year later", "3 years later", "5 years later", "Further fall to the final low", "Days until the final low", "Final low"],
        [[pct(a["threshold"], 0), a["peak_date"], a["hit_date"], pct(a.get("fwd_ret_1y")), pct(a.get("fwd_ret_3y")), pct(a.get("fwd_ret_5y")),
          pct(a.get("further_fall_to_final_low")), a.get("days_to_final_low"), a.get("final_low_date")] for a in d["after_threshold"]])
    skill = []
    for q, v in d["questions"].items():
        a, h = v.get("walk_forward_1950_1999") or {}, v.get("holdout_2000_latest") or {}
        skill.append([v["text"], pct(v["probabilities"].get("base")), num(a.get("skill_final"), 3), num(h.get("skill_final"), 3),
                      v.get("w_live"), h.get("n_event_episodes")])
    tab(wb, "Model skill",
        ["Question", "Historical odds", "Skill 1950-1999 (above 0 = better than historical odds)", "Skill 2000-now, untouched test", "Weight given to the model now (0 to 1)", "Separate events in the test"], skill)
    head, rows = read_csv(os.path.join(ROOT, "config", "master_notes.csv"))
    if rows:
        tab(wb, "Research notes", [h.capitalize() for h in head], rows)
    path = os.path.join(out_dir, "Market Monitor MASTER.xlsx")
    wb.save(path)
    return path


def build_weekly(d, out_dir):
    wb = Workbook()
    wb.remove(wb.active)
    sig, info, cape = d["signals"], d.get("feature_info", {}), d.get("cape_10y_real_return", {})
    rules = sig["rules"]
    n_v = sum(1 for r in rules if r["type"] == "vulnerability")
    n_t = sum(1 for r in rules if r["type"] == "trigger")
    summary = [
        ["As of", d["asof"]],
        ["S&P 500 close", num(d["sp500_last_close"])],
        ["Vulnerability signs switched on", f"{sig['vulnerability_on']} of {n_v}"],
        ["Trigger signs switched on", f"{sig['trigger_on']} of {n_t}"],
        ["Valuation (Shiller CAPE)", f"{num(cape.get('cape_now'), 1)}" + (" (estimate)" if cape.get("cape_is_estimate") else "")],
        ["Estimated real return per year over 10 years", f"{pct(cape.get('estimate_real_ann_10y'))} (likely range {pct(cape.get('band_1sd', [None, None])[0])} to {pct(cape.get('band_1sd', [None, None])[1])})"],
    ]
    for q, v in d["questions"].items():
        p = v["probabilities"]
        summary.append([v["text"], f"{pct(p.get('final'))} (historical odds {pct(p.get('base'))})"])
    summary += [
        ["Changes since last run", d.get("changes_line", "not tracked yet")],
        ["Prediction ledger check", d.get("ledger", {}).get("verify_message", "")],
        ["Data cautions", "; ".join(k for k in ["partial_month", "cape_is_estimate", "anchor_used"] if info.get(k)) or "none"],
    ]
    tab(wb, "Summary", ["Item", "Value"], summary)
    tab(wb, "Signals", ["Sign", "Kind", "Now", "Current reading", "Rule"],
        [[RULE_NAMES.get(r["rule"], r["rule"]), r["type"], r["state"], num(r.get("current_value"), 3), r["definition"]] for r in rules])
    tab(wb, "Probabilities", ["Question", "Historical odds", "Similar past months", "Regression", "Final", "Weight on the model"],
        [[v["text"], pct(v["probabilities"].get("base")), pct(v["probabilities"].get("analog")), pct(v["probabilities"].get("logit")),
          pct(v["probabilities"].get("final")), v.get("w_live")] for v in d["questions"].values()])
    market = [[SYMBOL_NAMES.get(s, s), num(m.get("last_close")), m.get("date"), f"{num(m.get('ytd_pct'), 1)}%", f"{num(m.get('pct_from_52w_high'), 1)}%"]
              for s, m in d["market_snapshot"].items() if isinstance(m, dict) and m.get("last_close") is not None]
    ws = tab(wb, "Market", ["Market", "Last close", "Date", "This year", "From 52-week high"], market)
    ws.append([])
    ws.append(["Canada and margin debt", "Latest", "Date", "About 12 months earlier", "Source"])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
    for r in canada_rows() + margin_rows():
        ws.append(r)
    tab(wb, "Analogs", ["Similar period starts", "Ends", "Months", "Average return over the next 12 months", "Worst fall in the next 12 months"],
        [[a["first"], a["last"], a["n_months"], pct(a.get("mean_next_12m_return")), pct(a.get("worst_drawdown_12m"))] for a in d["analogs"]])
    ph, pr = read_csv(os.path.join(ROOT, "ledger", "predictions.csv"))
    rh, rr = read_csv(os.path.join(ROOT, "ledger", "resolutions.csv"))
    res = {r[0]: r for r in rr}
    keep = ["id", "issued_at_utc", "question_id", "resolve_after", "p_base", "p_final", "w"]
    idx = [ph.index(k) for k in keep if k in ph]
    preds = []
    for r in pr:
        x = res.get(r[0])
        preds.append([r[i] for i in idx] + ([x[2], x[3], x[4]] if x else ["pending", "", ""]))
    tab(wb, "Predictions", ["Prediction", "Issued (UTC)", "Question", "Comes due", "Historical odds", "Forecast", "Weight", "Outcome (1 = happened)", "Error score, forecast", "Error score, historical odds"], preds)
    sc = d.get("scorecard", {}).get("by_question", {})
    tab(wb, "Scorecard", ["Question", "Issued", "Scored", "Pending", "Error score, forecast (lower is better)", "Error score, historical odds", "Skill"],
        [[q, s.get("n_issued"), s.get("n_resolved"), s.get("n_pending"), num(s.get("brier_final"), 4), num(s.get("brier_base"), 4), num(s.get("skill"), 3)] for q, s in sc.items()])
    ch, cr = read_csv(os.path.join(ROOT, "ledger", "changelog.csv"))
    tab(wb, "Changes", ch or ["Rule changes"], cr or [["No rule changes yet. The model needs 20 scored predictions per question before it adjusts."]])
    news = d.get("news") or []
    tab(wb, "Evidence", ["Date", "Source", "Headline", "Direction", "Note", "Link"],
        [[n.get("date"), n.get("source_domain"), n.get("headline"), n.get("direction"), n.get("note"), n.get("url")] for n in news]
        or [["", "", "No accepted news items this run.", "", "", ""]])
    path = os.path.join(out_dir, f"Market Monitor {d['asof']}.xlsx")
    wb.save(path)
    return path


def changes_line(d):
    """Save a small snapshot of this run in state/history/ and describe what moved since the previous one."""
    hist = os.path.join(ROOT, "state", "history")
    os.makedirs(hist, exist_ok=True)
    now = {"asof": d["asof"],
           "p": {q: v["probabilities"].get("final") for q, v in d["questions"].items()},
           "signals": {r["rule"]: r["state"] for r in d["signals"]["rules"]}}
    earlier = sorted(f for f in os.listdir(hist) if f.endswith(".json") and f[:-5] < d["asof"])
    with open(os.path.join(hist, f"{d['asof']}.json"), "w", encoding="utf-8") as f:
        json.dump(now, f, indent=1)
    if not earlier:
        return "first run, nothing to compare"
    with open(os.path.join(hist, earlier[-1]), encoding="utf-8") as f:
        prev = json.load(f)
    out = [f"{RULE_NAMES.get(k, k)} turned {s}" for k, s in now["signals"].items() if prev["signals"].get(k) not in (None, s)]
    for q, p in now["p"].items():
        old = prev["p"].get(q)
        if p is not None and old is not None and abs(p - old) >= 0.03:
            out.append(f"{q} {pct(old)} to {pct(p)}")
    resolved = d.get("ledger", {}).get("resolved_this_run") or 0
    if resolved:
        out.append(f"{resolved} predictions scored")
    return f"since {prev['asof']}: " + ("; ".join(out) if out else "no change")


# ---------------------------------------------------------------------------------------------------------
# Weekly exports (python -m mm.run weekly calls export_all): master workbook, weekly workbook, weekly_summary.md

QTEXT = {"dd10_3m": "closes 10%+ below today's close within the next 63 trading days",
         "down_12m": "closes lower 252 trading days from now"}


class Book:
    """Collects tabs; saves one .xlsx, or one CSV per tab when openpyxl is not installed."""

    def __init__(self):
        self.tabs = []

    def add(self, title, header, rows):
        self.tabs.append((title[:31], list(header), [list(r) for r in rows]))

    def save(self, path_xlsx):
        if HAVE_XLSX:
            wb = Workbook()
            wb.remove(wb.active)
            for t, h, r in self.tabs:
                tab(wb, t, h, r)
            wb.save(path_xlsx)
            return path_xlsx
        d = path_xlsx[:-5] + "_csv"
        os.makedirs(d, exist_ok=True)
        for t, h, r in self.tabs:
            with open(os.path.join(d, re.sub(r"[^A-Za-z0-9_-]+", "_", t) + ".csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(h)
                w.writerows(["" if v is None else v for v in row] for row in r)
        return d


def _r(x, d=2):
    return None if x is None else round(float(x), d)


def _p(x, d=1):
    return None if x is None else round(100 * float(x), d)


def buy_zone_table(L):
    zs = sorted({z for a in L["assets"] for z in map(int, a["zone_prices"])})
    head = ["Ticker", "Name", "Class", "Currency", "Last close", "Last date", "Record close", "Record date",
            "52-week high", "% below record"]
    head += [f"Zone {z}% price" for z in zs] + [f"Distance to {z}% zone (%)" for z in zs]
    head += ["Deepest zone entered", "Flag", "200-day average", "% vs 200-day", "Year to date (%)", "Note"]
    rows = []
    for a in sorted(L["assets"], key=lambda a: (-a["deepest_zone"], -a["pct_below_record"])):
        zp, zd = a["zone_prices"], a["zone_distance_pct"]
        rows.append([a["ticker"], a["name"], a["asset_class"], a["currency"], _r(a["last_close"], 4), a["last_date"],
                     _r(a["record_close"], 4), a["record_date"], _r(a["high_52w"], 4), _r(a["pct_below_record"], 1)]
                    + [_r(zp.get(str(z)), 4) for z in zs] + [_r(zd.get(str(z)), 1) for z in zs]
                    + [a["deepest_zone"] or "none", a.get("flag") or "", _r(a["ma200"], 4), _r(a["pct_vs_ma200"], 1),
                       _r(a["ytd_pct"], 1), a["note"]])
    return head, rows


def zone_history_table(L):
    head = ["Ticker", "Zone %", "Past episodes that crossed it", "Completed", "Median further fall (%)",
            "Worst further fall (%)", "Median days to low", "1y median (%)", "1y worst (%)", "1y positive (%)",
            "3y median (%)", "3y worst (%)", "3y positive (%)", "5y median (%)", "5y worst (%)", "5y positive (%)",
            "Cases at 1y / 3y / 5y"]
    rows = []
    for a in L["assets"]:
        for z, h in sorted(a["zone_history"].items(), key=lambda kv: int(kv[0])):
            rows.append([a["ticker"], int(z), h["n_episodes"], h["n_completed"], _p(h["further_fall_median"]),
                         _p(h["further_fall_worst"]), h["days_to_low_median"]]
                        + sum([[_p(h[f"fwd_{k}_median"]), _p(h[f"fwd_{k}_worst"]), _p(h[f"fwd_{k}_pct_positive"], 0)]
                               for k in ("1y", "3y", "5y")], [])
                        + [f"{h['fwd_1y_n']} / {h['fwd_3y_n']} / {h['fwd_5y_n']}"])
    return head, rows


def signal_table(L):
    head = ["Signal", "Meaning", "State now", "Reading", "Data month", "Months with data", "Months ON",
            "Hit rate 12m (%)", "Base rate 12m (%)", "Hit rate 24m (%)", "Base rate 24m (%)", "False-alarm rate 24m (%)",
            "Bears eligible", "Bears caught", "Median lead (months)", "Rule"]
    rows = [[x["signal"], x["label"], x["state"], _r(x["value"], 3), x["data_month"], x["months_defined"], x["months_on"],
             _p(x["hit_rate_12m"], 0), _p(x["base_rate_12m"], 0), _p(x["hit_rate_24m"], 0), _p(x["base_rate_24m"], 0),
             _p(x["false_alarm_24m"], 0), x["bears_eligible"], x["bears_caught"], _r(x["median_lead_months"], 1),
             x["definition"]] for x in L["signal_board"]["signals"]]
    return head, rows


def _split(qid):
    q, _, t = qid.partition("@")
    return q, t


def open_predictions(root=None):
    ph, pr = read_csv(os.path.join(root or ROOT, "ledger", "predictions.csv"))
    _, rr = read_csv(os.path.join(root or ROOT, "ledger", "resolutions.csv"))
    done = {r[0] for r in rr}
    i = {k: ph.index(k) for k in ph}
    rows = []
    for r in pr:
        if r[i["id"]] in done:
            continue
        q, t = _split(r[i["question_id"]])
        rows.append([r[i["asof_date"]], t or "^GSPC (S&P model)", q, QTEXT.get(q) or r[i["question_id"]],
                     r[i["resolve_after"]], _p(float(r[i["p_base"]]), 1), _p(float(r[i["p_model"]]), 1),
                     _p(float(r[i["p_final"]]), 1), float(r[i["w"]]), r[i["id"]]])
    return ["As of", "Asset", "Question", "Meaning", "Resolves after", "Base rate (%)", "Model (%)", "Forecast (%)",
            "Weight on model", "Ledger id"], rows


def accuracy_table(L):
    head = ["Question", "Asset class", "Issued", "Resolved (n)", "Model Brier", "Base-rate Brier", "Skill (1 - model/base)"]
    rows = [[a["question"], a["asset_class"], a["n_issued"], a["n_resolved"], _r(a["brier_model"], 4),
             _r(a["brier_base"], 4), _r(a["skill"], 3)] for a in L["accuracy"]]
    rows.append([])
    rows.append(["Historical walk-forward check (not live): weight chosen on days up to 2015, holdout 2016 to now. n counts overlapping days.", "", "", "", "", "", ""])
    for q, d in L.get("asset_backtest", {}).items():
        for cls, x in d["holdout_2016_latest"].items():
            rows.append([f"{q} (backtest, w={d['w_chosen_pre_2016']})", cls, "", x["n_days"], _r(x["brier_model"], 4),
                         _r(x["brier_base"], 4), _r(x["skill"], 3)])
    return head, rows


def manifest_table(L):
    head = ["Source", "Status", "Rows", "First date", "Last date", "Retrieved (UTC)", "sha256", "URL", "Error"]
    rows = [[k, v["status"], v.get("rows"), v.get("first_date"), v.get("last_date"), v.get("retrieved_at"),
             v.get("sha256"), v.get("url"), v.get("error")] for k, v in sorted(L["manifest"]["sources"].items())]
    return head, rows


def history_table(root=None):
    from . import changes
    rows = [[h["asof"], h["kind"], h["key"], h["state"], h["value"], h["extra"]] for h in changes.read_history(root)]
    return ["As of", "Kind", "Key (ticker or signal)", "State (deepest zone % or ON/OFF)",
            "Value (% below record, or signal reading)", "Last close"], rows


def dashboard_rows(L):
    sb, al = L["signal_board"], L["alerts"]
    in_zone = [a for a in L["assets"] if a["deepest_zone"]]
    fi = L["feature_info"]
    rows = [["As of", L["asof"]], ["S&P 500 close", _r(L["sp500_last_close"])],
            ["Alarm: S&P below 10-month average while CAPE in top 10%", sb["alarm_trend_and_cape90"]],
            ["Base signals ON", f"{sb['base_on']} of {sb['n_base']}"],
            ["Shiller CAPE", _r(L["features_today"].get("cape"), 1) if not fi["cape_is_estimate"] else f"{_r(L['features_today'].get('cape'), 1)} (estimate: reported earnings end before the lagged E10 month)"],
            ["Assets tracked", len(L["assets"])], ["Assets in a buy zone now", len(in_zone)]]
    for z in (10, 20, 30, 40):
        names = [a["ticker"] for a in in_zone if a["deepest_zone"] == z]
        rows.append([f"Deepest zone {z}%", ", ".join(names) or "none"])
    rows += [["Zone changes this run", ", ".join(f"{c['flag']} {c['ticker']}" for c in al["zone_changes"]) or "none"],
             ["Signal flips this run", ", ".join(f"{c['signal']} {c['from']}->{c['to']}" for c in al["signal_flips"]) or "none"],
             ["New predictions", f"{al['new_predictions']['sp500']} S&P model + {al['new_predictions']['assets']} asset"],
             ["Resolved this run", len(al["new_resolved"])], ["Ledger check", L["ledger"]["verify_message"]],
             ["Data problems", "; ".join(al["data_failures"]) or "none"]]
    return ["Item", "Value"], rows


def what_changed_table(L):
    from . import changes
    return ["What changed since last run"], [[x] for x in changes.what_changed_lines(L["alerts"])]


def summary_md(L, max_words=300):
    from . import changes
    sb, al = L["signal_board"], L["alerts"]
    a = [f"# Weekly summary, {L['asof']}", ""]
    on = sb["alarm_trend_and_cape90"]
    a.append(f"**Alarm line** (S&P below its 10-month average while CAPE is in its top 10%): **{on}**. "
             f"{sb['base_on']} of {sb['n_base']} tested warning signals are on.")
    a.append("")
    a.append("**What changed**")
    lines = changes.what_changed_lines(al)
    for x in lines[:6]:
        a.append(f"- {x}")
    if len(lines) > 6:
        a.append(f"- and {len(lines) - 6} more (see the workbook).")
    a.append("")
    a.append("**Buy zones** (distance below the all-time closing high)")
    for z in (40, 30, 20, 10):
        t = [x["ticker"] for x in L["assets"] if x["deepest_zone"] == z]
        if t:
            a.append(f"- {z}% zone: " + ", ".join(t[:12]) + (f" and {len(t) - 12} more" if len(t) > 12 else ""))
    near = sorted((x for x in L["assets"] if not x["deepest_zone"] and x["pct_below_record"] >= 7), key=lambda x: -x["pct_below_record"])
    if near:
        a.append("- close to the 10% zone: " + ", ".join(x["ticker"] for x in near[:6]))
    a.append(f"- {sum(1 for x in L['assets'] if not x['deepest_zone'])} of {len(L['assets'])} tracked assets are above the first zone.")
    a.append("")
    n = al["new_predictions"]
    a.append(f"Predictions: {n['sp500'] + n['assets']} new this week, {len(al['new_resolved'])} scored. "
             "In back-tests the forecasts add little over the plain historical odds. This is a statistical check, not advice.")
    if al["data_failures"]:
        a.append(f"Data problems: {len(al['data_failures'])} (see Sources tab).")
    txt = "\n".join(a) + "\n"
    while len(txt.split()) > max_words and len(a) > 8:        # drop lines from the middle sections if too long
        a.pop(next(i for i in range(len(a) - 1, 0, -1) if a[i].startswith("- ")))
        txt = "\n".join(a) + "\n"
    return txt


def export_all(L, root=None, out_dir=None):
    """Write master workbook, weekly workbook and weekly_summary.md into out/. Returns the paths written."""
    out_dir = out_dir or os.path.join(root or ROOT, "out")
    os.makedirs(out_dir, exist_ok=True)
    m = Book()
    m.add("Dashboard", *dashboard_rows(L))
    m.add("Buy zones", *buy_zone_table(L))
    m.add("Zone history", *zone_history_table(L))
    m.add("Signals", *signal_table(L))
    m.add("Predictions open", *open_predictions(root))
    m.add("Accuracy", *accuracy_table(L))
    m.add("History", *history_table(root))
    m.add("Sources", *manifest_table(L))
    w = Book()
    w.add("Buy zones", *buy_zone_table(L))
    w.add("Signals", *signal_table(L))
    w.add("What changed", *what_changed_table(L))
    ph, pr = open_predictions(root)
    w.add("New predictions", ph, [r for r in pr if r[0] == L["asof"]])
    paths = [m.save(os.path.join(out_dir, "market_monitor_master.xlsx")),
             w.save(os.path.join(out_dir, f"market_monitor_week_{L['asof']}.xlsx"))]
    p = os.path.join(out_dir, "weekly_summary.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(summary_md(L))
    return paths + [p]


def main():
    with open(os.path.join(ROOT, "state", "latest.json"), encoding="utf-8") as f:
        d = json.load(f)
    d["changes_line"] = changes_line(d)
    print("CHANGES:", d["changes_line"])
    out_dir = os.path.join(ROOT, "out")
    os.makedirs(out_dir, exist_ok=True)
    for p in (build_master(d, out_dir), build_weekly(d, out_dir)):
        with open(p, "rb") as f:
            print(f"{hashlib.sha256(f.read()).hexdigest()}  {p}")


if __name__ == "__main__":
    main()
