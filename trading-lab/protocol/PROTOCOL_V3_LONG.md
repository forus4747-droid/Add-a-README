# Protocol v3 — Phase 2: long-history, whole-market, self-fixing loop

Written before any Phase 2 result existed. Phase 1 (PROTOCOL.md) is closed and unchanged.

## Why a loop needs three tiers
A loop that keeps "fixing mistakes" against the same history eventually memorises that history. It will look
accurate and predict nothing. So the history is cut into three parts with different access:

| Tier | Dates | Who can read it | Purpose |
|---|---|---|---|
| LOOP | 1990-01-02 → 2012-12-31 | workers and reviewer | find mistake patterns, build fixes, measure them |
| CONFIRM | 2013-01-01 → 2019-12-31 | **reviewer only** | a fix is kept only if it also improves here |
| LOCKBOX | 2020-01-01 → 2026-11-12 | **nobody until the end** | one run of the final version |

- Workers get a copy of the data that ends on 2012-12-31 (`data_loop/`). The full file is kept encrypted;
  the reviewer decrypts it only to run a confirmation, then deletes the plaintext.
- Each confirmation leaks a little information back into the loop (accept / reject). The number of
  confirmations is capped at 8 and every one is logged in `reports/P2_loop_log.md`, accepted or not.
- After the lockbox run, the only remaining honest test is the future: forward predictions logged before
  the outcome is known.

## Data
- Source: Yahoo Finance chart API, daily, 1990-01-02 → 2025-12-31, every currently listed US common stock
  (~6,900 symbols) plus market series (SPY, sector ETFs, ^GSPC, ^VIX, ^TNX, ^IRX). Prices adjusted for
  splits and dividends. `scripts/fetch_yahoo_long.py`. (Step 3.15: Yahoo daily data agreed with Alpaca on
  99.9% of days.) 2026 is added only for the lockbox run.
- **Universe (point-in-time):** on each day, the 1,000 stocks with the highest median dollar volume over the
  previous 63 trading days (known the day before), with at least 252 days of history.
- **Known limitation — survivorship:** Yahoo has no delisted companies. Every stock in the 1990s sample
  survived to today. This inflates the *level* of returns for all methods and can flatter momentum, size and
  quality-type signals. It cannot be fixed with the sources available. It applies equally to LOOP, CONFIRM
  and LOCKBOX, so comparisons between versions stay fair; absolute return figures should not be trusted.

## What is predicted
- Main task: for every in-universe stock and day t, a score; compared with the return from open[t+1] to
  open[t+6] (same as Phase 1), ranked across the universe that day.
- Secondary task (risk): which stocks will MOVE most — score compared with |return| over the same window.
  Direction is hard; size of move may be predictable and is still useful (position sizing, stop distance).

## Metrics and pass mark (per tier)
For each year: rank IC, hit rate, top-minus-bottom quintile spread, top-quintile return net of 0.1%
round-trip cost vs equal-weight universe. Over a tier: mean of yearly ICs, share of years with IC > 0,
t-stat of the daily IC series (deflated for 5-day overlap).
**A version "predicts" on a tier if:** pooled t-stat > 3, IC positive in at least 75% of the years, and
top-quintile net excess > 0. (Stricter than Phase 1's t > 2 because many versions are tried.)

## Loop rules (details in `protocol/LOOP_RULES.md`)
1. Start from v0 = the Phase 1 final swing skill.
2. Each iteration, a worker (a) measures where the current best version is wrong on LOOP data — by year,
   market regime, volatility, liquidity, score decile, after large moves; (b) states ONE hypothesis for the
   mistake pattern; (c) builds the fix as a new version; (d) measures it on LOOP data with the fixed harness.
3. The reviewer re-runs it, checks causality, and scores it on CONFIRM. Kept only if CONFIRM mean IC and
   share of positive years are both at least as good as the current best and one is strictly better.
4. Anything that learns from data must be refit walk-forward (a model predicting year Y sees only labels
   that were known before Y began).
5. Stop after 8 confirmations or two consecutive rejections with no new idea.
