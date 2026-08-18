# Verification log — 18 Aug 2026

An attempt to verify the demand signals against primary sources instead of vendor blogs.
Recording what was checked, what could not be, and one metric that broke under testing.

## Access

| Route | Result |
|---|---|
| Direct fetch (curl) | **Blocked.** Gateway returns 403 CONNECT for `apps.shopify.com`, `chromewebstore.google.com`, `ycombinator.com`, `paulgraham.com`, `shopify.dev`. Org egress policy — not routed around. |
| Firecrawl MCP | **Worked once**, then hit the free rate limit. One live page retrieved. |
| Apify actor | **Ran**, aborted at a $0.55 platform cost cap after 111 rows — and the category endpoint returns no review counts, so it did not produce the needed metric. |
| GitHub clone | Works. Used to verify repos and commit dates. |

**Cost incurred: up to $0.55 of Apify credit, for data that did not answer the question.**
Recorded because it was the user's money.

## ✅ Verified from primary source

From the live Shopify App Store (Firecrawl, HTTP 200, cache miss):

| Fact | Value |
|---|---|
| Total apps | **"over 16,000"** — Shopify's own copy |
| App review process | 100-checkpoint review before listing |
| Judge.me Product Reviews | **43,600** reviews, 5.0★ |
| Shopify Flow | 12,017 reviews, 4.7★ |
| Shop | 8,428 reviews, 4.8★ |
| Shopify Inbox | 5,490 reviews, 4.6★ |
| Smile: Loyalty | 4,187 reviews, 4.9★ |

**This corrects an earlier figure.** Vendor sources put the catalogue at 7,954 rated apps or
13,786 analysed. Shopify says over 16,000.

Also visible: several first-party Shopify apps rate poorly — Search & Discovery **2.7★**,
Bundles **2.8★**, Subscriptions **3.7★**, Order Printer **3.6★**. Weak incumbents in
categories Shopify itself occupies. Worth a second look; not yet screened.

## ❌ The metric broke under testing

`DEMAND-SIGNALS.md` proposed **reviews ÷ listings vs the marketplace baseline** as the
primary demand signal. Product Reviews looked like the standout: 77,625 reviews across 347
apps = **224 per app, 2.4× the 92 baseline.**

Live data kills that reading:

```
Judge.me alone                    43,600 reviews  =  56.2% of the entire category
All other 346 apps combined       34,025 reviews
Mean for everyone else            98 reviews/app  =  1.07x baseline
```

**One app holds the majority of the category. Strip it out and the category is average.**

The category did not look attractive because demand outstripped supply. It looked
attractive because a **mean was computed across a power law**, and the winner dragged it up.
Reading that as "merchants are searching and not finding enough" inverts the truth: they
searched, they found Judge.me, and they stopped looking.

### The corrected metric

A mean over a power-law distribution measures the leader, not the market. Use instead:

1. **Leader review share** — reviews of the #1 app ÷ category total. **High share = closed.**
   The primary reading.
2. **Median** reviews per app, never the mean.
3. **Reviews of the #5–10 apps** — if the tail is starving, the category is winner-take-all.

A category is genuinely open when demand is **high and spread**, not high and concentrated.

## ⚠️ Still unverified

- Marketplace baseline of 92 reviews/app — traces to a single vendor blog
- "Six categories above 250 reviews/app" — same source, and now suspect for the reason above
- "40% of ad-spending stores have no retention app" — single source, unverified
- Every Chrome Web Store and micro-SaaS revenue figure

To verify properly: a full catalogue scrape with per-app review counts (Apify `app`
scrapeType, ~16,000 apps), costing a few dollars and a raised cost cap.

## What this changes

Saturation observed live in the crawl — **subscriptions** (8+ competing apps in the visible
listing), **print-on-demand/dropshipping** (12+), **B2B wholesale pricing** (8+) — is
consistent with the earlier read and is real.

But no category has been confirmed as genuinely open. The one that looked best is now the
clearest example of the measurement error. **No idea should be built on this data yet.**

---

# Round 2 — all remote routes exhausted

Attempted the full catalogue scrape. Every available route is now blocked:

| Route | Result |
|---|---|
| Direct fetch (curl) | **403** at the egress gateway — org policy, not routed around |
| Apify — `scoutlayer` | Aborted at a **$0.55** platform cost cap; endpoint returns no review counts |
| Apify — `fatihtahta` | **"Monthly usage hard limit exceeded"** — account quota spent. Confirmed it *does* return `reviewCount`, `ratingBreakdown`, `pricing`, `launched` — the right actor, no quota to run it |
| Firecrawl | Free-tier rate limit, both attempts |
| WebSearch | Works, but returns vendor summaries — the thing being checked |

**Total spend: up to $0.55 of Apify credit, for data that did not answer the question.**

## The fix: stop depending on any of them

`tools/leader_share.py` runs on a normal machine, which has no egress policy and no API
quota. Only dependency is `requests`.

```bash
python3 research/tools/leader_share.py --pages 15
```

It paginates each category, parses every listing's review count, and reports the readings
that survive a power-law distribution:

| Column | Meaning |
|---|---|
| **LEAD%** | Leader's share of all category reviews. **≥40% = closed.** |
| **TOP3%** | Top three combined. ≥65% = closed. |
| **MEDIAN** | Median reviews per app — printed beside MEAN so the distortion is visible |
| **TAIL** | Median reviews for apps ranked 5–15. Under 50 = winner-take-all |

Verdicts are mechanical: `CLOSED`, `WINNER-TAKE-ALL`, `CONTESTED`, `OPEN`. A category is
`OPEN` only when demand is high **and spread** — leader under 20% with a healthy tail.

Outputs `shopify_categories_apps.csv` (every app) and `_summary.json` (per-category stats).

**Two honest limits.** Sampling the top N pages biases toward the head, so leader share is
an **upper** bound — raise `--pages` until the numbers stop moving. And if Shopify changes
their markup the regex breaks; the script says so rather than reporting silently wrong
numbers.

## Alternatives if you would rather not run it

1. **Firecrawl free API key** (firecrawl.dev/signin) — set as an `Authorization: Bearer` header on the connector. Removes the rate limit; I could then do it from here.
2. **Apify quota reset** next billing cycle. `fatihtahta/shopify-app-store-scraper` at ~$0.002/app — the whole catalogue is roughly $32, one category about $0.50.

## Status

**No category is confirmed open.** The strongest-looking candidate turned out to be the
clearest case of the measurement error. Nothing here supports building yet.

---

# Round 3 — real data obtained, via the one open channel

Retried Firecrawl (still rate-limited) and Apify (still over monthly limit). Then used
**GitHub**, which is the only unrestricted channel, and found a published Shopify App Store
dataset: `markthomas93/Shopify-App-Store-Data-Science` (originating from Kaggle).

Committed to `research/data/` — 2,510 apps, 3,530 category rows, 287,453 reviews.
Analysis script: `research/tools/analyse_dataset.py`.

## ⚠️ Vintage: 2019

Last commit **2019-03-04**. The store held **2,510 apps** then; Shopify's own site now says
**over 16,000**. **This data cannot tell us where opportunity is in 2026** and no current
conclusion should be drawn from the category rankings below.

What it *can* do is settle two methodological questions with real numbers, and that turns
out to be the more valuable result.

## Finding 1 — the "reviews per app" baseline is meaningless

| Statistic | Value |
|---|---|
| **Mean** reviews per app | **128** |
| **Median** reviews per app | **8** |
| Apps with **zero** reviews | **13.6%** |

**The mean is 16× the median.** Every vendor analysis — and my own earlier one — compared
categories against a *mean* baseline of ~92. A mean over this distribution measures the
winners, not the market. **Any category comparison built on it is invalid**, including the
"six categories above 250 reviews/app" claim.

The honest base rate for a new app: **half of all apps have 8 or fewer reviews**, and one in
seven has none at all. Not "under $1,000/month" — under ten reviews, ever.

## Finding 2 — leader share is scale-dependent *(a new flaw in my own metric)*

Per-category concentration on this data (2019, historical only):

| Category | Apps | Leader % | Top-3 % | Median | Mean | Leader |
|---|---:|---:|---:|---:|---:|---|
| Places to sell | 66 | 11.1 | 30.8 | 9 | 47 | Facebook channel |
| Store design | 1,025 | 11.2 | 27.4 | 9 | 157 | Privy |
| Orders and shipping | 397 | 14.1 | 26.1 | 6 | 49 | AfterShip |
| Sales and conversion | 618 | 14.5 | 29.0 | 11 | 187 | Sales Pop |
| Inventory management | 154 | 15.2 | 28.9 | 8 | 37 | Bulk Product Edit |
| Finding/adding products | 126 | 15.9 | 37.2 | 15 | 112 | Oberlo |
| Reporting | 150 | 17.3 | 35.1 | 3 | 23 | Compass |
| Marketing | 545 | 17.5 | 30.1 | 11 | 188 | Privy |
| Productivity | 95 | 20.0 | 55.2 | 9 | 57 | Kit |
| Finances | 77 | 21.4 | 40.5 | 3 | 21 | Data Export |
| Customer support | 205 | 26.8 | 49.5 | 5 | 78 | Answers |
| **Trust and security** | 72 | **54.7** | 73.6 | 7 | 80 | EU Cookie Bar |

Most leaders hold only 11–27% — which would read as "open". **That reading is an artifact of
bucket width.**

Compare directly against the live 2026 figure: in the *subcategory* **Product Reviews**,
Judge.me holds **56%**. But "Store design" — 1,025 apps wide — shows its leader at 11%.

**Leader share dilutes as the bucket widens.** Measured on a top-level nav category it will
almost always look open; measured on the subcategory a buyer actually shops in, the same
market can be closed. Only "Trust and security" (72 apps, narrow) showed as closed here —
and narrowness is exactly why it was visible.

**Correction: always measure at the level the buyer shops at, never the top-level category.**

## Status

Two real methodological corrections, both from data rather than argument. Still **no current
category is confirmed open**, and the 2019 rankings must not be used as if they were.

To get current readings: run `research/tools/leader_share.py` locally against the live store,
applied to **subcategories**, not the seven top-level ones.
