---
name: opportunity-screen
description: Kill a business idea before building it. Runs eight ordered falsification gates — software substitute, incumbent services, existing budget line, reachable distribution, why-now, schlep test, public pain evidence, unit economics — each with a hard kill criterion and a required evidence standard. Use BEFORE writing any offer, landing page, pricing, outreach or playbook, and whenever the user proposes a business idea, service offer, product concept, niche, or asks "would this work" / "is there a market for". Also use to audit an offer that was already built.
---

# Opportunity Screen

**Rule zero: no artefact gets built until every gate passes.** No offer doc, no pricing,
no landing page, no outreach sequence. Building first and screening after produces
confident, well-written work about a dead idea.

A screen costs ~30 minutes and about 15 searches. Building first costs hours and
produces something that has to be retracted.

## Why this exists

The failure mode this prevents: an idea is plausible, the writing is good, the economics
look fine on paper — and a single search that was never run ("does software already do
this?") would have killed it in four minutes.

**More research does not fix this.** A deep-research agent answers the question it is
given. If the killing question is never asked, a better engine returns a longer,
better-cited report about a dead idea. The discipline is the ordered list of questions,
not the tooling.

## The gates

Run in order. **Stop at the first kill.** They are ordered cheapest-kill-first, so most
dead ideas die in gate 1 or 2 for a few minutes of searching.

### Gate 1 — Software substitute
> Does software already do this, and what does it charge?

Search: `"<deliverable> software pricing"`, `"<category> tools comparison 2026"`,
`"best <category> software for <buyer>"`, then the top 3 vendors' pricing pages.

**KILL IF** a funded company ships this as an automated feature at or below the intended
price. You are not entering a market, you are entering a price war against a sales team.

**SURVIVES IF** software exists but demonstrably fails at adoption — look for reviews
citing setup burden, lock-in contracts, surprise billing, abandoned seats. That is a
services gap, and it is a *narrower, lower-margin* business than a true product gap.
Say so explicitly rather than treating it as a clean pass.

### Gate 2 — Incumbent services
> Who already sells this as a service, and what do they charge?

Search: `"<service> agency pricing"`, `"<service> monthly retainer cost"`,
`"white label <service> reseller"`.

**KILL IF** established agencies sell it at the intended price and there is no stated
edge beyond being cheaper. Cheaper is not an edge when the buyer cannot verify quality
before purchase.

**KILL IF** a mature white-label reseller ecosystem exists — the margin is already
competed away.

### Gate 3 — Existing budget line
> Does this buyer already spend money on this specific thing?

Search actual spend data, not intent surveys: `"<buyer> spend on <category> per month"`,
`"percentage of <buyer> that pay for <category>"`.

**KILL IF** there is no existing budget line. Creating a new budget category is the
hardest sale that exists. Claimed interest is not spend — always find the payment number,
not the survey number.

### Gate 4 — Reachable distribution
> Can you list 200 of these buyers, with contact details, without paying for access?

**KILL IF** there is no public directory, searchable map, registry, or member list.
**KILL IF** reaching them requires an introduction, a conference, or a licence you lack.

Rank the channel honestly against benchmarks — cold email averages ~3.4% reply, under 2%
in software verticals, ~5.8% on hand-built lists under 50.

### Gate 5 — Why now
> What changed in the last 18 months that makes this possible, and wasn't true before?

**KILL IF** nothing changed AND the idea has been technically possible for years AND
nobody does it. That combination usually means it has been tried and does not work.

The exception is gate 6 — check it before killing on this one.

### Gate 6 — The schlep test *(the only reliable positive signal)*
> Is this tedious, unglamorous, or unpleasant enough that competent people avoid it?

Per Paul Graham's *schlep blindness*: ideas behind a schlep filter stay underexplored
because people unconsciously route around them. For someone with no special access, no
capital, and no audience, **this is the strongest available edge** — it is the one moat
that does not require money or reputation.

**WEAK IF** the work is pleasant, fashionable, or the subject of current course-selling.
Fashionable categories are saturated by definition — everyone was taught the same play.

### Gate 7 — Public pain evidence
> Can you find 10 real, dated, linkable people describing this problem in public?

Forums, subreddits, review sites, support threads, G2/Capterra complaints.

**KILL IF** you cannot find the pain in public. You are imagining the problem.
**KILL IF** every complaint you find is from vendors marketing a solution to it.

Each piece of evidence gets a confidence tag (see below). Ten weak citations do not
add up to one strong one.

### Gate 8 — Unit economics
> Price ÷ delivery hours. Churn. Acquisition cost in units of work.

- **KILL IF** effective rate is under ~$100/hour after the offer matures
- **KILL IF** the buyer's DIY cost is an order of magnitude below the price and the
  difference cannot be justified by an outcome they cannot reach themselves
- **KILL IF** projected churn exceeds ~5%/month — small agencies run 25–32% annual churn,
  so assume worse when solo
- Express acquisition cost in emails-or-calls per closed client, not dollars

## Evidence standard

Tag every figure. Never present a WEAK figure as settled.

| Tag | Means |
|---|---|
| `STRONG` | Peer-reviewed study, regulatory filing, government dataset, company investor relations |
| `MODERATE` | Credible industry report or vendor pricing page read directly |
| `WEAK` | SEO aggregator, single secondary source, unverifiable, or a number that traces back to one analyst |

Rules:
- **Cross-check any figure that decides a gate** against an independent source. If both
  trace to the same origin, it is one source, not two.
- **State when a primary source could not be opened.** Never imply a document was read
  when only a search summary of it was.
- **Name the survivorship problem** whenever citing public revenue figures. Everyone who
  ran the same play and failed is absent from the sample, and that denominator is
  usually uncollected.

## Output

Report a verdict table, then the recommendation. Nothing else.

| Gate | Verdict | Evidence | Confidence |
|---|---|---|---|
| 1 Software substitute | PASS / **KILL** | one line + link | STRONG/MODERATE/WEAK |
| … | | | |

Then one of:
- **KILLED at gate N** — state the reason in one sentence. Do not soften it, do not
  propose a rescue in the same breath, and do not build anything.
- **SURVIVES** — state the single weakest gate, because that is what will actually
  fail in practice, and what the cheap test should be aimed at.

## After a pass

Only now design the falsifiable test: smallest spend, fastest signal, kill criteria
fixed in writing *before* execution begins — because they will be renegotiated later,
and that is exactly when they need to already exist.

## Sources worth screening against

- **Vendor pricing pages** — gate 1 and 2 live here. Read them directly, not via roundups.
- **G2 / Capterra / Trustpilot negative reviews** — where the adoption gap in gate 1 is visible.
- **Paul Graham, *How to Get Startup Ideas*** — organic ideas, live-in-the-future, schlep blindness. Gate 6.
- **YC Requests for Startups** (ycombinator.com/rfs) — useful as a signal of where capital
  is pointed. **Not an idea source for a bootstrapped solo operator**: recent RFS entries
  need millions in funding and technical teams. Take the method from YC, not the list.
