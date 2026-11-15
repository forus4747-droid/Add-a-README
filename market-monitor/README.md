# market-monitor

A small forecasting and self-scoring engine for the S&P 500, plus a buy-zone and prediction tracker for a
configurable list of assets. Python 3 stdlib + numpy + pandas (openpyxl only for the .xlsx export, xlrd for Shiller's file).
Every week it refreshes data, rebuilds a no-look-ahead monthly feature table, backtests simple models
walk-forward, issues probabilistic predictions into a tamper-evident ledger, scores the ones that have
matured, and nudges each question's blend weight by one small step.

## Run

```
python -m mm.run weekly      # refresh -> features -> backtest -> resolve -> self-correct -> issue -> assets/zones -> signals ->
                             #   alerts -> state/latest.json, REPORT.md, out/*.xlsx, out/weekly_summary.md
                             #   exits 1 with a message if key data (S&P, VIX, CPI, bills, FINRA, BoC, Shiller) is stale
python -m mm.run backtest    # recompute the walk-forward backtest (no cache) and print the summary
python -m mm.run verify      # recompute the ledger hash chain
python -m mm.run news FILE   # validate a JSON list of news items against config/allowlist.txt
python -m tests.test_sanity  # plain-assert tests (uses data/raw cache)
```
A weekly run takes about 10 to 20 seconds (it re-downloads everything, about 90 small files, in parallel).

## What the weekly job does
1. Downloads every source (failures are recorded in `data/raw/manifest.json`; the cached copy is kept, nothing is invented)
   and stops with a non-zero exit if a key input is older than its limit.
2. Rebuilds features and the walk-forward backtest, resolves matured predictions (S&P and assets), and, only if something
   new was scored, moves each question's weight by one 0.05 step when at least 20 live predictions exist.
3. Issues the S&P questions and, for every tracked asset with 10+ years of daily history, two asset questions.
4. Computes buy zones for all assets in `config/assets.csv`, the tested signal board, and compares with the previous run
   (`state/zones_state.json`, `state/signals_state.json`) to write `state/alerts.json` and the "What changed" lists.
5. Appends one row per asset and signal to `state/weekly_history.csv` (replaces the same as-of date), then writes
   `out/market_monitor_master.xlsx` (Dashboard, Buy zones, Zone history, Signals, Predictions open, Accuracy, History,
   Sources), `out/market_monitor_week_YYYY-MM-DD.xlsx` and `out/weekly_summary.md` (under 300 words). `out/` is git-ignored;
   without openpyxl one CSV per tab is written to `out/<name>_csv/`.
Commit `ledger/`, `state/` and `REPORT.md` after each run; they are the memory of the system.

## Layout
`mm/data.py` download + cache + `data/raw/manifest.json` (url, retrieved_at, rows, first/last date, sha256);
raises if the last ^GSPC close is more than 5 days old. `mm/features.py` month-end features.
`mm/targets.py` forward outcomes. `mm/episodes.py` drawdown episodes. `mm/models.py` models and backtest.
`mm/signals.py` rules board. `mm/ledger.py`, `mm/selfcorrect.py` ledger and weights. `mm/news.py` news gate.
`mm/assets.py` + `config/assets.csv` asset universe, record highs, zones, per-zone history, ENTERED/EXITED flags.
`mm/assetpred.py` asset predictions and live accuracy table. `mm/changes.py` previous-run comparison, alerts, history csv.
`mm/sheets.py` workbook, CSV and weekly summary export. `mm/report.py` renders REPORT.md from `state/latest.json` only. `ledger/` and `state/weights.json` are the
persistent state; `ledger/*.csv` are append-only.

## Sources
Shiller's current ie_data.xls found through shillerdata.com (the file is hosted on img1.wsimg.com), with the GitHub
mirror (datasets/s-and-p-500) only as fallback; Yahoo chart API for the model inputs (^GSPC, ^TNX, ^IRX, ^VIX, HYG, RSP,
SPY, BZ=F, NVDA, GOOG ...) and for every ticker in `config/assets.csv`; FRED CSV (CPIAUCSL, UNRATE, TB3MS, GS10, BAA, AAA,
BAMLH0A0HYM2, WTISPLC); FINRA margin statistics xlsx (www.finra.org); Bank of Canada Valet JSON (policy rate V39079,
5-year yield BD.CDN.5YR.DQ.YLD). Yahoo bar dates use the exchange time zone from the response. A failed download is recorded in the manifest (status, error), the cached copy is kept
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

* Buy zones: zone z% = all-time closing high x (1 - z/100) for z in the asset's `zones` (default 10, 20, 30, 40). Funds
  flagged `use_adjclose` use Yahoo's distribution-adjusted close (last adjusted value = last close, so prices are on
  today's scale); indices, futures, FX, crypto and single stocks use plain closes. Episodes run from one record close to the
  next; per zone the history lists episodes that crossed it, the further fall from the first crossing to the episode low
  (completed episodes only), days to that low, and returns 1/3/5 years (252/756/1260 bars) after the first crossing where
  that much data exists. Flags compare the deepest zone entered with the previous run's state.
* Tested signal board (`mm/signals.py`, `tested_board`): 13 base signals (CAPE > 30, CAPE above its expanding 90th
  percentile, inverted curve, 3m bill +1.5 pt in 12m, CPI > 4% and rising, BAA-AAA +0.3 pt in 6m, HY OAS > 5% and +1.5 pt in
  3m, S&P below 10-month average, Sahm-style +0.5 pt, WTI +50%, RSP-SPY <= -5 pt, FINRA margin debt +30% (lagged one month),
  VIX > 30), the combo "CAPE top 10% and trend broken" and "4 or more ON". Event = S&P daily close 20% below the month-end
  close within 12 (24) months. Hit rate, base rate, false-alarm rate (24m), and bears caught (signal ON in the 12 months
  up to a >= 20% bear market's peak, for bears starting after the signal's first month) are recomputed every run.
  Today's state uses the latest published value of each series.
* Asset predictions: for each asset with >= 10 years of daily history, "closes >= 10% below today's close at some point in
  the next 63 bars" and "closes lower 252 bars from now". p_base = share of past days with a finished outcome window;
  p_model = share among past days in the same drawdown bucket (<5, 5-10, 10-20, 20-30, 30+% below the record) and on the same
  side of the 200-day average, shrunk toward p_base with 20 pseudo-days; p_final = p_base + w (p_model - p_base). The start
  weight per question is chosen on days up to 2015 (grid 0 to 1), later days are the holdout reported in the Accuracy tab;
  after that `ledger/changelog.csv` records live one-step changes. Ids in the ledger look like `dd10_3m@NVDA`.

## Limits (read these)
* The asset model is only drawdown bucket x trend state. In the 2016-now holdout it has essentially no skill over the plain
  base rate (skill about -1% to 0), and the 12-month "closes lower" weight was chosen as 0. Live accuracy needs resolved
  predictions: the first 63-bar questions resolve in about 3 months.
* HY OAS exists on FRED only from 2023-11 here, so that signal has no usable history. Narrow-market (RSP from 2003) and
  margin debt (FINRA from 1997) have only 3 and 4 eligible bear markets; small counts mean little weight.
* Futures series are continuous front-month contracts and roll gaps are not adjusted; non-positive prices are dropped.
  Crypto trades every day, so "63 trading days" means 63 daily bars. Zone prices for USD/CAD (CAD=X) measure falls in that
  quote, i.e. a stronger Canadian dollar.
* Assets are cut at the S&P's as-of date, so every row in a week uses the same date; a bar for a 24-hour market at that
  date may be partial.
* Shiller's earnings column is blank after 2026-06 in the current file; his PE10 keeps moving on an extrapolated E10, so
  CAPE is flagged `cape_is_estimate` when the lagged E10 month is past the last reported earnings.
* Skill is small. In the 2000-latest holdout the 1- and 3-month questions are about at the base-rate level and the
  12-month drawdown questions are worse than the base rate. Treat probabilities as calibrated history, not forecasts.
* Outcomes overlap heavily, so the effective sample is the number of distinct episodes (reported), not months.
* Dividends are missing in Shiller's file after 2023-06, so the 10-year real return targets end around 2013; with the
  GitHub mirror as fallback the old stale-CAPE problem returns (the flag is set).
* The CAPE 10-year estimate is an in-sample regression on overlapping windows.
* Pre-1928 prices are monthly averages; pre-1957 ^GSPC is the S&P 90 composite; ^IRX replaces TB3MS from 1960.
* A single unpublished CPI month (2025-10) is log-interpolated; UNRATE gaps are left missing (trailing minimum uses
  at least 10 of 12 months).
* The latest month is partial; its momentum uses a date lookup instead of month-end shift.
* News is only validated, never scored or fed to the models.

## What cannot be automated
* A scheduled run must be started by something (cron, a scheduler); this repo does not run itself.
* News: reading and choosing items is manual (`python -m mm.run news FILE`); the gate only checks the host allowlist,
  link, date and freshness, and news never changes a number.
* Sources are scraped endpoints (Yahoo chart API, shillerdata.com page, FINRA file path); any of them can change or block.
  A failure shows in the Sources tab and in "What changed", and an outdated key input stops the run.
* Judgement about whether a zone is a buy is yours; the tool only reports distances and history.
