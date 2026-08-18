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
