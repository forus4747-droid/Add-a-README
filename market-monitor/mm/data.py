"""Download + cache raw inputs, write data/raw/manifest.json."""
import hashlib
import io
import json
import os
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

import pandas as pd

from . import ROOT

SHILLER_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv"
YAHOO_URL = ("https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
             "?period1=-2000000000&period2=9999999999&interval=1d")
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
FINRA_URL = "https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx"
BOC_URL = "https://www.bankofcanada.ca/valet/observations/{sid}/json?recent=3000"
BOC_SERIES = {"V39079": "Bank of Canada policy rate (%)", "BD.CDN.5YR.DQ.YLD": "Canada 5-year bond yield (%)"}

YAHOO_SYMBOLS = ["^GSPC", "^TNX", "^IRX", "^VIX", "^GSPTSE", "XEQT.TO", "CAD=X", "NVDA", "GOOG",
                 "HYG", "RSP", "SPY", "BZ=F", "GC=F", "DX-Y.NYB", "^IXIC", "BTC-USD"]
FRED_SERIES = ["CPIAUCSL", "UNRATE", "TB3MS", "GS10", "BAA", "AAA", "BAMLH0A0HYM2", "WTISPLC"]
MAX_STALE_DAYS = 5


def asset_tickers(root=None):
    """Tickers in config/assets.csv (the tracked universe); empty list if the file is missing."""
    import csv
    p = os.path.join(root or ROOT, "config", "assets.csv")
    if not os.path.exists(p):
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return [r["ticker"].strip() for r in csv.DictReader(f) if r.get("ticker", "").strip()]


def yahoo_symbols(root=None):
    return list(dict.fromkeys(YAHOO_SYMBOLS + asset_tickers(root)))


def raw_dir(root=None):
    d = os.path.join(root or ROOT, "data", "raw")
    os.makedirs(d, exist_ok=True)
    return d


def _ctx():
    for p in (os.environ.get("SSL_CERT_FILE"), os.environ.get("CURL_CA_BUNDLE"),
              os.environ.get("REQUESTS_CA_BUNDLE"), "/root/.ccr/ca-bundle.crt"):
        if p and os.path.exists(p):
            return ssl.create_default_context(cafile=p)
    return ssl.create_default_context()


def _get(url, tries=3, timeout=60, ua="Mozilla/5.0"):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
                return r.read()
        except Exception as e:  # noqa
            last = e
    raise RuntimeError(f"{type(last).__name__}: {last}")


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _parse_yahoo(raw):
    j = json.loads(raw)
    res = j["chart"]["result"][0]
    tz = res["meta"].get("exchangeTimezoneName")
    off = res["meta"].get("gmtoffset", 0) or 0
    ts = res["timestamp"]
    close = res["indicators"]["quote"][0]["close"]
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose") or close
    df = pd.DataFrame({"t": ts, "close": close, "adjclose": adj})
    df["adjclose"] = df["adjclose"].fillna(df["close"])
    df = df.dropna(subset=["close"])
    try:   # bar date = calendar date at the exchange (handles daylight saving; a fixed offset does not)
        df["date"] = pd.to_datetime(df["t"], unit="s", utc=True).dt.tz_convert(tz).dt.tz_localize(None).dt.normalize()
    except Exception:  # unknown or missing time zone name
        df["date"] = pd.to_datetime(df["t"] + off, unit="s").dt.normalize()
    df = df.drop_duplicates("date", keep="last")[["date", "close", "adjclose"]]
    return df


def _drop_partial_today(df, now):
    """Drop a bar dated today (UTC) if the US cash close has not happened yet (21:30 UTC)."""
    if len(df) and df["date"].iloc[-1].date() == now.date() and (now.hour, now.minute) < (21, 30):
        return df.iloc[:-1], True
    return df, False


MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10,
          "nov": 11, "dec": 12}
OFFICIAL_COLS = {1: "SP500", 2: "Dividend", 3: "Earnings", 4: "Consumer Price Index", 6: "Long Interest Rate",
                 7: "Real Price", 8: "Real Dividend", 10: "Real Earnings", 12: "PE10"}


def find_xls_url(html):
    """First URL in the page containing ie_data.xls (protocol-relative URLs get https:)."""
    import re
    for m in re.finditer(r"""(?:https?:)?//[^"'\s<>]*ie_data\.xls[^"'\s<>]*""", html):
        u = m.group(0).replace("&amp;", "&")
        return "https:" + u if u.startswith("//") else u
    return None


def parse_official_xls(content):
    """Parse sheet 'Data' of Shiller's ie_data.xls into the mirror's schema (NaN where missing)."""
    import xlrd
    wb = xlrd.open_workbook(file_contents=content)
    sh = wb.sheet_by_name("Data")
    hdr = None
    for r in range(sh.nrows):
        if str(sh.cell_value(r, 0)).strip().lower() == "date" and "cape" in str(sh.cell_value(r, 12)).lower():
            hdr = r
            break
    if hdr is None:
        raise RuntimeError("header row (Date ... CAPE) not found")
    rows, notes = [], []
    for r in range(hdr + 1, sh.nrows):
        v = sh.cell_value(r, 0)
        if isinstance(v, (int, float)) and v != "":
            ym = f"{float(v):.2f}"
            y, m = int(ym.split(".")[0]), int(ym.split(".")[1])
            if not (1 <= m <= 12):
                continue
            rec = {"Date": pd.Timestamp(year=y, month=m, day=1)}
            for c, name in OFFICIAL_COLS.items():
                x = sh.cell_value(r, c)
                rec[name] = float(x) if isinstance(x, (int, float)) else float("nan")
            rows.append(rec)
        else:
            for c in range(sh.ncols):
                t = str(sh.cell_value(r, c))
                if t.strip():
                    notes.append(t)
    df = pd.DataFrame(rows)
    # months whose CPI the sheet itself flags as estimated are blanked (FRED CPI takes over downstream)
    import re
    for t in notes:
        if "cpi" in t.lower() and "estimat" in t.lower():
            ms = [MONTHS[w[:3]] for w in re.findall(r"[A-Za-z]+", t.lower()) if w[:3] in MONTHS]
            last = df["Date"].iloc[-1]
            for mm_ in ms:
                sel = (df["Date"].dt.year == last.year) & (df["Date"].dt.month == mm_)
                df.loc[sel, "Consumer Price Index"] = float("nan")
    return df


def fetch_official(now):
    """Return (DataFrame, extra manifest fields). Raises on failure."""
    html = None
    err = None
    for base in ("https://shillerdata.com/", "https://www.shillerdata.com/"):
        try:
            html = _get(base, tries=2, timeout=40).decode("utf8", "ignore")
            url = find_xls_url(html)
            if url:
                break
        except Exception as e:  # noqa
            err = e
    else:
        raise RuntimeError(f"ie_data.xls link not found ({err})")
    content = _get(url, tries=2, timeout=90)
    df = parse_official_xls(content)
    return df, {"xls_url": url, "xls_sha256": _sha(content)}


def parse_finra(content):
    """FINRA margin statistics xlsx -> DataFrame(date = first day of month, debit = $ millions, free_credit_cash,
    free_credit_margin), ascending."""
    df = pd.read_excel(io.BytesIO(content))
    df = df.iloc[:, :4]
    df.columns = ["ym", "debit", "free_credit_cash", "free_credit_margin"]
    df["date"] = pd.to_datetime(df["ym"].astype(str), format="%Y-%m", errors="coerce")
    df["debit"] = pd.to_numeric(df["debit"], errors="coerce")
    df = df.dropna(subset=["date", "debit"]).sort_values("date")
    if df.empty:
        raise RuntimeError("no monthly rows in FINRA file")
    return df[["date", "debit", "free_credit_cash", "free_credit_margin"]]


def parse_boc(raw, sid):
    """Bank of Canada Valet JSON -> DataFrame(date, value), ascending."""
    j = json.loads(raw)
    rows = [(o["d"], float(o[sid]["v"])) for o in j["observations"] if o.get(sid, {}).get("v") not in (None, "")]
    if not rows:
        raise RuntimeError("Valet returned no observations")
    df = pd.DataFrame(rows, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")


def refresh(root=None, only=None):
    """Download everything; on failure keep cached file (if any) and record the failure."""
    rd = raw_dir(root)
    mpath = os.path.join(rd, "manifest.json")
    try:
        manifest = json.load(open(mpath))
    except Exception:
        manifest = {}
    manifest.pop("extras", None)          # entry left by an earlier version
    now = datetime.now(timezone.utc)
    jobs = [("shiller", SHILLER_URL, "shiller.csv")]
    jobs += [(f"yahoo:{s}", YAHOO_URL.format(sym=urllib.parse.quote(s, safe="")), f"yahoo_{s}.csv")
             for s in yahoo_symbols(root)]
    jobs += [("shiller_official", "https://shillerdata.com/", "shiller_official.csv")]
    jobs += [(f"fred:{s}", FRED_URL.format(sid=s), f"fred_{s}.csv") for s in FRED_SERIES]
    jobs += [("finra:margin", FINRA_URL, "finra_margin.csv")]
    jobs += [(f"boc:{s}", BOC_URL.format(sid=s), f"boc_{s}.csv") for s in BOC_SERIES]
    def one(job):
        key, url, fname = job
        path = os.path.join(rd, fname)
        ent = {"url": url, "attempted_at": now.isoformat(timespec="seconds"), "status": "ok", "error": None,
               "dropped_partial_today_bar": False}
        try:
            raw = _get(url, ua="curl/8.0", timeout=30, tries=2) if key.startswith("fred:") else _get(url)
            if key == "shiller_official":
                df, extra = fetch_official(now)
                ent.update(extra)
                dates = df["Date"]
                body = df.to_csv(index=False).encode()
            elif key == "finra:margin":
                df = parse_finra(raw)
                dates = df["date"]
                body = df.to_csv(index=False).encode()
            elif key.startswith("boc:"):
                df = parse_boc(raw, key[4:])
                dates = df["date"]
                body = df.to_csv(index=False).encode()
            elif key == "shiller":
                df = pd.read_csv(io.BytesIO(raw))
                df["Date"] = pd.to_datetime(df["Date"])
                dates = df["Date"]
                body = df.to_csv(index=False).encode()
            elif key.startswith("yahoo:"):
                df = _parse_yahoo(raw)
                df, dropped = _drop_partial_today(df, now)
                ent["dropped_partial_today_bar"] = dropped
                dates = df["date"]
                body = df.to_csv(index=False).encode()
            else:
                df = pd.read_csv(io.BytesIO(raw))
                dcol = df.columns[0]
                vcol = df.columns[1]
                df[dcol] = pd.to_datetime(df[dcol])
                df[vcol] = pd.to_numeric(df[vcol], errors="coerce")
                df = df.dropna()
                if df.empty:
                    raise RuntimeError("FRED returned no numeric rows")
                df.columns = ["date", "value"]
                dates = df["date"]
                body = df.to_csv(index=False).encode()
            with open(path, "wb") as f:
                f.write(body)
            ent.update(retrieved_at=now.isoformat(timespec="seconds"), rows=int(len(df)),
                       first_date=str(dates.iloc[0].date()), last_date=str(dates.iloc[-1].date()),
                       sha256=_sha(body), file=fname)
        except Exception as e:  # record failure, keep any cache, never invent
            old = manifest.get(key, {})
            ent.update(status="failed", error=str(e)[:300], file=fname if os.path.exists(path) else None,
                       using_cache=os.path.exists(path))
            for k in ("retrieved_at", "rows", "first_date", "last_date", "sha256"):
                if k in old:
                    ent[k] = old[k]
        return key, ent

    from concurrent.futures import ThreadPoolExecutor
    jobs = [j for j in jobs if not only or j[0] in only]
    with ThreadPoolExecutor(8) as ex:
        for key, ent in ex.map(one, jobs):
            manifest[key] = ent
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    check_fresh(root)
    return manifest


def check_fresh(root=None, today=None):
    y = load_yahoo("^GSPC", root)
    if y is None:
        raise RuntimeError("no ^GSPC data available")
    today = today or datetime.now(timezone.utc).date()
    age = (today - y.index[-1].date()).days
    if age > MAX_STALE_DAYS:
        raise RuntimeError(f"^GSPC last date {y.index[-1].date()} is {age} days old (> {MAX_STALE_DAYS})")
    return age


def key_data_problems(root=None, today=None):
    """Stale key inputs (list of messages, empty if all fresh). Ages are measured from the last observation date."""
    today = pd.Timestamp(today or datetime.now(timezone.utc).date())
    man = load_manifest(root)
    limits = {"yahoo:^GSPC": 5, "yahoo:^VIX": 7, "fred:CPIAUCSL": 100, "fred:TB3MS": 100, "fred:UNRATE": 100,
              "fred:BAA": 100, "finra:margin": 100, "boc:V39079": 20}
    limits["shiller_official" if shiller_source(root) == "official" else "shiller"] = 150
    out = []
    for k, lim in limits.items():
        e = man.get(k)
        if not e or not e.get("last_date"):
            out.append(f"{k}: no data")
            continue
        age = (today - pd.Timestamp(e["last_date"])).days
        if age > lim:
            out.append(f"{k}: last observation {e['last_date']} is {age} days old (limit {lim})"
                       + (f"; download failed: {e.get('error')}" if e.get("status") != "ok" else ""))
    return out


def load_manifest(root=None):
    try:
        return json.load(open(os.path.join(raw_dir(root), "manifest.json")))
    except Exception:
        return {}


def load_yahoo(sym, root=None):
    p = os.path.join(raw_dir(root), f"yahoo_{sym}.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p, parse_dates=["date"])
    return df.set_index("date")["close"].astype(float)


def load_yahoo_adj(sym, root=None):
    """Dividend/split-adjusted close (used for HYG, RSP, SPY relative-return and drawdown rules)."""
    p = os.path.join(raw_dir(root), f"yahoo_{sym}.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p, parse_dates=["date"])
    col = "adjclose" if "adjclose" in df.columns else "close"
    return df.set_index("date")[col].astype(float)


def load_fred(sid, root=None):
    p = os.path.join(raw_dir(root), f"fred_{sid}.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p, parse_dates=["date"])
    return df.set_index("date")["value"].astype(float)


def _last_valid_pe(df):
    v = df["PE10"].replace(0.0, float("nan")).dropna()
    return v.index[-1] if len(v) else None


def load_finra(root=None):
    """FINRA margin debt ($ millions) indexed by month start; None if never downloaded."""
    p = os.path.join(raw_dir(root), "finra_margin.csv")
    if not os.path.exists(p):
        return None
    return pd.read_csv(p, parse_dates=["date"]).set_index("date")["debit"].astype(float)


def load_boc(sid, root=None):
    p = os.path.join(raw_dir(root), f"boc_{sid}.csv")
    if not os.path.exists(p):
        return None
    return pd.read_csv(p, parse_dates=["date"]).set_index("date")["value"].astype(float)


def load_shiller_mirror(root=None):
    p = os.path.join(raw_dir(root), "shiller.csv")
    return pd.read_csv(p, parse_dates=["Date"]).set_index("Date")


def load_shiller_official(root=None):
    p = os.path.join(raw_dir(root), "shiller_official.csv")
    if not os.path.exists(p):
        return None
    return pd.read_csv(p, parse_dates=["Date"]).set_index("Date")


def load_shiller(root=None):
    """Official Shiller ie_data.xls (current) whenever it downloaded and has a valid PE10; the GitHub mirror
    only as fallback."""
    return load_shiller_official(root) if shiller_source(root) == "official" else load_shiller_mirror(root)


def shiller_source(root=None):
    o = load_shiller_official(root)
    if o is not None and _last_valid_pe(o) is not None:
        return "official"
    return "mirror"


def load_anchor(root=None):
    try:
        return json.load(open(os.path.join(root or ROOT, "state", "cape_anchor.json")))
    except Exception:
        return None


def save_anchor(anchor, root=None):
    d = os.path.join(root or ROOT, "state")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "cape_anchor.json"), "w") as f:
        json.dump(anchor, f, indent=1)


def load_all(root=None):
    return {"shiller": load_shiller(root), "shiller_source": shiller_source(root), "cape_anchor": load_anchor(root),
            "yahoo": {s: load_yahoo(s, root) for s in YAHOO_SYMBOLS},
            "yahoo_adj": {s: load_yahoo_adj(s, root) for s in ("HYG", "RSP", "SPY")},
            "fred": {s: load_fred(s, root) for s in FRED_SERIES},
            "finra": load_finra(root), "boc": {s: load_boc(s, root) for s in BOC_SERIES}}
