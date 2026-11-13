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

YAHOO_SYMBOLS = ["^GSPC", "^TNX", "^IRX", "^VIX", "^GSPTSE", "XEQT.TO", "CAD=X", "NVDA", "GOOG",
                 "HYG", "RSP", "SPY", "BZ=F", "GC=F", "DX-Y.NYB", "^IXIC", "BTC-USD"]
FRED_SERIES = ["CPIAUCSL", "UNRATE", "TB3MS", "GS10", "BAA", "AAA", "BAMLH0A0HYM2", "WTISPLC"]
MAX_STALE_DAYS = 5


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
    off = res["meta"].get("gmtoffset", 0) or 0
    ts = res["timestamp"]
    close = res["indicators"]["quote"][0]["close"]
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose") or close
    df = pd.DataFrame({"t": ts, "close": close, "adjclose": adj})
    df["adjclose"] = df["adjclose"].fillna(df["close"])
    df = df.dropna(subset=["close"])
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


def refresh(root=None, only=None):
    """Download everything; on failure keep cached file (if any) and record the failure."""
    rd = raw_dir(root)
    mpath = os.path.join(rd, "manifest.json")
    try:
        manifest = json.load(open(mpath))
    except Exception:
        manifest = {}
    now = datetime.now(timezone.utc)
    jobs = [("shiller", SHILLER_URL, "shiller.csv")]
    jobs += [(f"yahoo:{s}", YAHOO_URL.format(sym=urllib.parse.quote(s, safe="")), f"yahoo_{s}.csv")
             for s in YAHOO_SYMBOLS]
    jobs += [("shiller_official", "https://shillerdata.com/", "shiller_official.csv")]
    jobs += [(f"fred:{s}", FRED_URL.format(sid=s), f"fred_{s}.csv") for s in FRED_SERIES]
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
    try:
        from . import extras
        for k, e in extras.refresh_extras(root, now).items():
            manifest[k] = e
    except Exception as e:  # never let optional blocks break the refresh
        manifest["extras"] = {"status": "failed", "error": str(e)[:300]}
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


def load_shiller_mirror(root=None):
    p = os.path.join(raw_dir(root), "shiller.csv")
    return pd.read_csv(p, parse_dates=["Date"]).set_index("Date")


def load_shiller_official(root=None):
    p = os.path.join(raw_dir(root), "shiller_official.csv")
    if not os.path.exists(p):
        return None
    return pd.read_csv(p, parse_dates=["Date"]).set_index("Date")


def load_shiller(root=None):
    """Official Shiller file if it has a valid PE10 later than the mirror, else the mirror."""
    m = load_shiller_mirror(root)
    o = load_shiller_official(root)
    if o is not None:
        lo, lm = _last_valid_pe(o), _last_valid_pe(m)
        if lo is not None and (lm is None or lo > lm):
            return o
    return m


def shiller_source(root=None):
    m = load_shiller_mirror(root)
    o = load_shiller_official(root)
    if o is not None:
        lo, lm = _last_valid_pe(o), _last_valid_pe(m)
        if lo is not None and (lm is None or lo > lm):
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
            "fred": {s: load_fred(s, root) for s in FRED_SERIES}}
