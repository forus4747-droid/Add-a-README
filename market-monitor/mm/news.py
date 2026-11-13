"""Validate news items against an allowlist and freshness rules."""
import csv
import glob
import json
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

from . import ROOT

DIRECTIONS = {"risk_up", "risk_down", "neutral"}
MAX_AGE_DAYS = 10


def load_allowlist(root=None):
    p = os.path.join(root or ROOT, "config", "allowlist.txt")
    with open(p) as f:
        return [ln.strip().lower() for ln in f if ln.strip() and not ln.startswith("#")]


def _dom_ok(dom, allow):
    dom = dom.lower().strip()
    return any(dom == a or dom.endswith("." + a) for a in allow)


def _accepted_urls(root):
    urls = set()
    for p in glob.glob(os.path.join(root or ROOT, "news", "accepted", "*.json")):
        try:
            for it in json.load(open(p)):
                urls.add(it.get("url"))
        except Exception:
            pass
    return urls


def validate(items, root=None, today=None):
    """Return (accepted, rejected[(item, reason)])."""
    today = today or datetime.now(timezone.utc).date()
    allow = load_allowlist(root)
    seen = _accepted_urls(root)
    acc, rej = [], []
    if not isinstance(items, list):
        return [], [({"raw": str(items)[:200]}, "input is not a JSON list")]
    for it in items:
        if not isinstance(it, dict):
            rej.append(({"raw": str(it)[:200]}, "item is not an object"))
            continue
        url = (it.get("url") or "").strip() if isinstance(it.get("url"), str) else ""
        reason = None
        if not url:
            reason = "missing url"
        elif url in seen:
            reason = "duplicate url"
        else:
            dom = it.get("source_domain")
            host = (urlparse(url).hostname or "").lower()
            if not isinstance(dom, str) or not dom.strip():
                reason = "missing source_domain"
            elif not _dom_ok(dom, allow):
                reason = f"domain not in allowlist: {dom}"
            elif not (host == dom.lower() or host.endswith("." + dom.lower())):
                reason = f"url host {host} does not match source_domain {dom}"
            else:
                try:
                    d = datetime.strptime(str(it.get("date")), "%Y-%m-%d").date()
                    if d > today:
                        reason = "date in the future"
                    elif (today - d).days > MAX_AGE_DAYS:
                        reason = f"date older than {MAX_AGE_DAYS} days"
                except Exception:
                    reason = "missing or invalid date (YYYY-MM-DD)"
            if reason is None:
                if not isinstance(it.get("headline"), str) or not it["headline"].strip():
                    reason = "missing headline"
                elif it.get("direction") not in DIRECTIONS:
                    reason = "direction must be one of risk_up, risk_down, neutral"
        if reason:
            rej.append((it, reason))
        else:
            seen.add(url)
            acc.append({k: it.get(k) for k in ("date", "url", "source_domain", "headline", "tag", "direction", "note")})
    return acc, rej


def ingest(items, root=None, today=None):
    root = root or ROOT
    today = today or datetime.now(timezone.utc).date()
    acc, rej = validate(items, root, today)
    os.makedirs(os.path.join(root, "news", "accepted"), exist_ok=True)
    if acc:
        p = os.path.join(root, "news", "accepted", f"{today}.json")
        prev = []
        if os.path.exists(p):
            prev = json.load(open(p))
        with open(p, "w") as f:
            json.dump(prev + acc, f, indent=1)
    if rej:
        lp = os.path.join(root, "news", "rejections.csv")
        new = not os.path.exists(lp)
        with open(lp, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["logged_at_utc", "url", "reason", "item_json"])
            for it, r in rej:
                w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            it.get("url") if isinstance(it, dict) else "", r, json.dumps(it)[:2000]])
    return acc, rej


def recent_accepted(root=None, today=None):
    today = today or datetime.now(timezone.utc).date()
    out = []
    for p in sorted(glob.glob(os.path.join(root or ROOT, "news", "accepted", "*.json"))):
        try:
            for it in json.load(open(p)):
                d = datetime.strptime(it["date"], "%Y-%m-%d").date()
                if 0 <= (today - d).days <= MAX_AGE_DAYS:
                    out.append(it)
        except Exception:
            pass
    return out
