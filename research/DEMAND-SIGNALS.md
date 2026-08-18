# Demand signals found — 18 Aug 2026

Run demand-first: locate a measured imbalance, *then* look at supply. Every figure carries a
confidence tag. Primary pages could not be opened from this environment (egress blocked), so
`MODERATE` means a credible source read via search summary, not a page read directly.

---

## The metric that makes this computable

**Reviews ÷ listings, compared to the marketplace baseline.**

A marketplace publishes both numbers. Their ratio measures demand concentrated on supply:
buyers arrived wanting something and found few options, so the few that exist absorb all the
installs and reviews. It is the closest thing to a public demand-to-supply reading available
to someone with no data of their own.

**Shopify App Store baseline: 92 reviews per app**, across 7,954 apps with ≥1 review.
`MODERATE`

## Where demand exceeds supply on Shopify

| Signal | Reading | vs baseline | Conf |
|---|---|---|---|
| Six categories average **250+ reviews per app** | Merchants searching, not finding enough | **2.7×** | `MODERATE` |
| **Product Reviews**: 77,625 reviews / 347 apps | ~224 per app — highest per-app demand in the catalogue | **2.4×** | `MODERATE` |
| Cited example: 24 apps, **581 reviews per app** | Enormous demand on tiny supply | **6.3×** | `WEAK` — category unnamed in source |

## Where supply is piling in — avoid

| Category | Signal | Conf |
|---|---|---|
| **SEO** | 139 new apps launched in a single month; hundreds established | `MODERATE` |
| **Analytics** | 188 new launches in a month; hundreds established | `MODERATE` |
| Shipping Labels, Discounts | Among the highest app counts on the store | `MODERATE` |

**These are where everyone builds.** High new-listing velocity is the inverse signal: a
category actively absorbing supply is filling up, whatever its current ratio says.

## Unserved population share — the buyers are already spending

| Signal | Conf |
|---|---|
| **40% of stores running paid ads have zero retention apps** — spending on acquisition, leaking on the back end | `MODERATE` |
| 88.4% of high-traffic stores running Meta ads have **no SMS marketing** | `MODERATE` |
| 84.9% have **no loyalty program**; 87.7% **collect no reviews** | `MODERATE` |
| 98.5% lack support apps · 98.3% subscriptions · 98.2% analytics · 95.3% reviews · 70.7% email | `MODERATE` |
| **76.6% of live Shopify apps ship English-only** | `MODERATE` |

The ad-spend figure is the strongest of these: it proves budget exists *and* names the leak.

## Pricing-shape gap

In analytics-reporting, 36% of apps offer a "free tier" that locks meaningful features behind
a ~$147 plan — merchants install, hit the wall, churn in week one. The stated opening is a
genuinely free tier that completely solves one use case, plus a ~$29 tier that adds depth.
`WEAK` — single source, and it is a vendor blog.

## Untracked query volume — a closing window

Conversational queries surfaced by AI assistants do not yet appear in Ahrefs or Semrush with
meaningful tracked volume, so they are effectively uncontested. `WEAK` — widely asserted by
SEO vendors who profit from the claim. **Verify the demand is real before acting on the
scarcity.** Uncontested and nonexistent look identical from the outside.

---

## Base rates — what these marketplaces actually pay

| Channel | Median | Top decile | Conf |
|---|---|---|---|
| **Shopify apps** | under **$1,000/mo**; a meaningful share earn nothing | top 10% $5k–50k MRR; top 1% $100k+ MRR | `MODERATE` |
| **Chrome extensions** | $100–500/mo at 1k–5k users, 6–12 months in | $2k–10k/mo at 10k+ users | `WEAK` |
| **Micro-SaaS generally** | ~70% under $1k MRR; median *profitable* ~$4,200 MRR | — | `MODERATE` |
| **AI wrappers** | **60–70% earn zero**; 80–95% fail | only 3–5% reach $10k MRR | `MODERATE` |

Shopify keeps developers on **100% of their first $1M** in gross app revenue (from Jan 2025),
15% above that. `MODERATE` — an unusually favourable split worth verifying directly.

### The comparison that matters

**Gumroad median: $72/month. Shopify app median: under $1,000/month.**

Same power-law shape, roughly an order of magnitude apart in the median. The difference is
not the product — it is that the marketplace supplies distribution to buyers who already run
revenue-generating businesses. **For someone with no audience, the marketplace is the
distribution**, and that is the single most important structural fact in this document.

## Honest counterweights

- The distribution is real but **the power law is still brutal** — a meaningful share of Shopify apps earn nothing.
- **AI wrappers are the base case to avoid**: 60–70% earn zero. Build time collapsing ~70% means building is no longer the moat, so a thin wrapper has none.
- Every marketplace figure here is **survivorship-exposed**. Nobody publishes the app that shipped and got 40 installs.
- The gap data comes from **vendors selling gap-analysis tools**. Their incentive is to make gaps look plentiful. Treat category-level claims as leads to verify, not findings.

## Next step

Pick 2–3 categories above the baseline, then run **Phase B** on each: strict domination,
incumbents, budget, distribution, why-now. Most will die there. That is the process working.
