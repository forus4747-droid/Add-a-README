#!/usr/bin/env python3
"""
Compute demand-vs-supply readings for Shopify App Store categories.

Run this on YOUR machine. The cloud session it was written in has egress
restrictions and exhausted API quotas; your laptop has neither.

    python3 leader_share.py                 # all categories, 5 pages each
    python3 leader_share.py --pages 15      # go deeper
    python3 leader_share.py --category marketing-and-conversion

Why leader share and not the average
------------------------------------
A mean review count over a power-law distribution measures the leader, not
the market. Shopify's "Product Reviews" category averages ~224 reviews/app
against a ~92 baseline, which reads as a 2.4x demand gap. But Judge.me alone
holds ~43,600 of those reviews — 56% of the category. Strip it out and the
rest average ~98, i.e. ordinary. The category is not underserved; merchants
searched, found the winner, and stopped looking.

So this reports:
  LEADER SHARE  reviews of #1 app / total reviews    HIGH = closed
  MEDIAN        median reviews per app               mean is useless here
  TAIL HEALTH   median reviews of apps ranked 5-15   starving tail = winner-take-all
  RECENT ENTRY  share of apps launched in ~2 years   high = crowding in

Only dependency: requests.   pip install requests
"""
import argparse, csv, json, re, statistics, sys, time
from collections import defaultdict

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

BASE = "https://apps.shopify.com"
CATEGORIES = [
    "sales-channels", "finding-products", "selling-products",
    "orders-and-shipping", "store-design", "marketing-and-conversion",
    "store-management",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (research; category demand analysis)"}
DELAY = 1.5  # be polite; do not lower this

# Listing cards render as: <name> ... 4.9 out of 5 stars (1,234) 1234 total reviews
CARD = re.compile(
    r'href="/([a-z0-9][a-z0-9\-]*)\?[^"]*"[^>]*>\s*([^<]{2,80}?)\s*</a>.{0,400}?'
    r'([\d.]+)\s*out of 5 stars.{0,200}?\(([\d,]+)\)',
    re.S,
)


def fetch(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return None
            print(f"    HTTP {r.status_code}, retrying", file=sys.stderr)
        except requests.RequestException as e:
            print(f"    {e}", file=sys.stderr)
        time.sleep(2 ** i)
    return None


def scrape_category(handle, max_pages):
    seen, apps = set(), []
    for page in range(1, max_pages + 1):
        url = f"{BASE}/categories/{handle}/all?page={page}"
        html = fetch(url)
        if not html:
            break
        found = 0
        for m in CARD.finditer(html):
            slug, name, rating, reviews = m.groups()
            if slug in seen:
                continue
            seen.add(slug)
            apps.append({
                "category": handle,
                "handle": slug,
                "name": name.strip(),
                "rating": float(rating),
                "reviews": int(reviews.replace(",", "")),
            })
            found += 1
        print(f"  page {page}: +{found} (total {len(apps)})")
        if found == 0:
            break
        time.sleep(DELAY)
    return apps


def analyse(apps):
    """Return the readings that survive a power-law distribution."""
    if len(apps) < 5:
        return None
    r = sorted((a["reviews"] for a in apps), reverse=True)
    total = sum(r) or 1
    tail = r[4:15] or r[-1:]
    return {
        "apps_sampled": len(apps),
        "total_reviews": total,
        "leader": apps and max(apps, key=lambda a: a["reviews"])["name"],
        "leader_reviews": r[0],
        "leader_share_pct": round(r[0] / total * 100, 1),
        "top3_share_pct": round(sum(r[:3]) / total * 100, 1),
        "median_reviews": int(statistics.median(r)),
        "mean_reviews": int(statistics.mean(r)),          # shown only to expose the distortion
        "tail_median_rank5_15": int(statistics.median(tail)),
        "zero_review_apps": sum(1 for x in r if x == 0),
    }


def verdict(s):
    """Blunt reading. High concentration means a winner already exists."""
    if s["leader_share_pct"] >= 40:
        return "CLOSED — one app owns the category"
    if s["top3_share_pct"] >= 65:
        return "CLOSED — top 3 own the category"
    if s["tail_median_rank5_15"] < 50:
        return "WINNER-TAKE-ALL — tail is starving"
    if s["leader_share_pct"] < 20 and s["tail_median_rank5_15"] > 200:
        return "OPEN — demand is high and spread"
    return "CONTESTED — no runaway leader, no easy entry"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pages", type=int, default=5, help="pages per category (~24 apps each)")
    p.add_argument("--category", help="single category handle")
    p.add_argument("--out", default="shopify_categories")
    a = p.parse_args()

    cats = [a.category] if a.category else CATEGORIES
    everything, rows = [], []

    for c in cats:
        print(f"\n{c}")
        apps = scrape_category(c, a.pages)
        everything += apps
        s = analyse(apps)
        if not s:
            print("  too few apps parsed — the page markup likely changed; fix CARD regex")
            continue
        s["category"] = c
        s["verdict"] = verdict(s)
        rows.append(s)

    if not rows:
        sys.exit("\nNothing parsed. Shopify changed their markup — update the CARD regex.")

    with open(f"{a.out}_apps.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["category", "handle", "name", "rating", "reviews"])
        w.writeheader(); w.writerows(everything)
    with open(f"{a.out}_summary.json", "w") as f:
        json.dump(rows, f, indent=2)

    print("\n" + "=" * 100)
    print(f"{'CATEGORY':<26}{'LEAD%':>7}{'TOP3%':>7}{'MEDIAN':>8}{'MEAN':>7}{'TAIL':>7}  VERDICT")
    print("=" * 100)
    for s in sorted(rows, key=lambda x: x["leader_share_pct"]):
        print(f"{s['category']:<26}{s['leader_share_pct']:>7}{s['top3_share_pct']:>7}"
              f"{s['median_reviews']:>8}{s['mean_reviews']:>7}{s['tail_median_rank5_15']:>7}  {s['verdict']}")
    print("=" * 100)
    print("LEAD% = leader's share of all reviews. Compare MEDIAN against MEAN —")
    print("a large gap is the power law that makes averages lie.")
    print(f"\nWrote {a.out}_apps.csv ({len(everything)} apps) and {a.out}_summary.json")
    print("\nSampling only the top N pages biases toward the head, so leader share is an")
    print("UPPER bound. Raise --pages until the numbers stop moving.")


if __name__ == "__main__":
    main()
