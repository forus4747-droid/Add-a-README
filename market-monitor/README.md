# market-monitor

A small forecasting and self-scoring engine for the S&P 500. Python 3 stdlib + numpy + pandas only.
Every week it refreshes data, rebuilds a no-look-ahead monthly feature table, backtests simple models
walk-forward, issues probabilistic predictions into a tamper-evident ledger, scores the ones that have
matured, and nudges each question's blend weight by one small step.

## Run

```
python -m mm.run weekly      # refresh -> features -> backtest (cached) -> resolve -> self-correct -> issue -> state/latest.json + REPORT.md
python -m mm.run backtest    # recompute the walk-forward backtest (no cache) and print the summary
python -m mm.run verify      # recompute the ledger hash chain
python -m mm.run news FILE   # validate a JSON list of news items against config/allowlist.txt
python -m tests.test_sanity  # plain-assert tests (uses data/raw cache)
```
A weekly run takes a few seconds with a warm cache (well under the 3 minute budget).

## Layout
`mm/data.py` download + cache + `data/raw/manifest.json` (url, retrieved_at, rows, first/last date, sha256);
raises if the last ^GSPC close is more than 5 days old. `mm/features.py` month-end features.
`mm/targets.py` forward outcomes. `mm/episodes.py` drawdown episodes. `mm/models.py` models and backtest.
`mm/signals.py` rules board. `mm/ledger.py`, `mm/selfcorrect.py` ledger and weights. `mm/news.py` news gate.
`mm/report.py` renders REPORT.md from `state/latest.json` only. `ledger/` and `state/weights.json` are the
persistent state; `ledger/*.csv` are append-only.

## Sources
Shiller monthly mirror (github datasets/s-and-p-500); Yahoo chart API (^GSPC, ^TNX, ^IRX, ^VIX, ^GSPTSE, XEQT.TO,
CAD=X, NVDA, GOOG, HYG, RSP, SPY, BZ=F, GC=F, DX-Y.NYB, ^IXIC, BTC-USD); FRED CSV (CPIAUCSL, UNRATE, TB3MS, GS10,
BAA, AAA, BAMLH0A0HYM2). A failed download is recorded in the manifest (status, error), the cached copy is kept
and nothing is invented. FRED rejects a browser User-Agent (the request hangs), so it is fetched with a curl UA.
A Yahoo bar dated today (UTC) is dropped before the US close so a partial day is never treated as a close.
HYG, RSP and SPY rules use Yahoo's adjusted close (distribution-adjusted); all else uses plain close.

## Method
* Features (month-end, 1881 to latest, units: infl/rates in percent, the rest fractions). Shiller CPI lagged 1 month,
  Shiller earnings-based E10 lagged 3 months. Price is the Yahoo month-end close from 1928 and Shiller's monthly
  average (ratio-spliced, ratio about 1.000) before. CAPE = month-end close / (CPI-lagged) / lagged real E10 backed out
  of Shiller PE10. After the last valid PE10 (2023-09 in the current file) real E10 is held constant and
  `cape_is_estimate` is set. CPI after Shiller's last month is extended with FRED CPIAUCSL chained at the last
  overlap. Momentum, 10-month trend, drawdown from running max (daily), 63-day realised vol (1928+), curve, bill and
  credit-spread changes, unemployment gap (UNRATE lagged one month) follow the spec.
* Targets: forward return and minimum close over 21/63/252 trading days (window includes day t); seven events.
  Shiller-style annualised real total returns over 3/5/10 years from month-end price, dividends/12, CPI.
* Models, per event, walk-forward monthly from 1950 using only rows whose outcome window had ended by that date:
  expanding base rate; 60 nearest analogs on expanding z-scores of 8 features; ridge logistic regression (IRLS,
  lambda 1, standardised, refit every 12 months). p_model is the mean of analog and logit;
  p_final = base + w (p_model - base). w in {0,.25,.5,.75,1} is chosen on 1950-1999 (only months whose outcome was
  resolved by end-1999), 2000-latest is the holdout; a second w chosen on all data is used live as the starting weight.
* Ledger: each prediction row is hashed with the previous row's hash (sha256). `verify` recomputes the chain.
  Issuing twice for one asof date adds nothing. Resolutions are appended once the 21/63/252 trading days exist.
* Self-correction: per question, with at least 20 resolved live predictions, w moves +0.05 if live Brier skill vs
  base is positive, else -0.05, clipped to [0,1], one step per run, logged in `ledger/changelog.csv`.

## Limits (read these)
* Skill is small. In the 2000-latest holdout the 1- and 3-month questions are about at the base-rate level and the
  12-month drawdown questions are worse than the base rate. Treat probabilities as calibrated history, not forecasts.
* Outcomes overlap heavily, so the effective sample is the number of distinct episodes (reported), not months.
* Shiller's file ends valid earnings/CPI/PE10/dividend data in 2023, so the current CAPE uses a stale (held-constant)
  real E10 and likely overstates CAPE; 10-year real return targets end in 2013 (dividends missing after 2023-06).
* The CAPE 10-year estimate is an in-sample regression on overlapping windows.
* Pre-1928 prices are monthly averages; pre-1957 ^GSPC is the S&P 90 composite; ^IRX replaces TB3MS from 1960.
* A single unpublished CPI month (2025-10) is log-interpolated; UNRATE gaps are left missing (trailing minimum uses
  at least 10 of 12 months).
* The latest month is partial; its momentum uses a date lookup instead of month-end shift.
* News is only validated, never scored or fed to the models.
