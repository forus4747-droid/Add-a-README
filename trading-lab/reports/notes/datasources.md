# Data source accuracy: yfinance and OpenBB vs trusted Alpaca SIP daily

Script: `scripts/test_data_sources.py` (fetch, then analyze). Outputs: `results/datasources_summary.csv` (plus `_mismatches`, `_splits`, `_ohlcv_detail`, `_stability`).
Window 2016-01-04 to 2025-12-31 (end=2026-01-01 exclusive). Max date in any downloaded file: 2025-12-31. No 2026 rows were requested or stored.

## Versions and environment
- yfinance 1.7.0 (core env), pandas 2.3.3. OpenBB: `openbb` 5.0.0, `openbb-core` 2.0.1 (openbb env). pyarrow was already present in the openbb env, so nothing was installed.
- Network: only Yahoo reachable. `fc.yahoo.com` (cookie/crumb) is blocked, so every yfinance call logs "Cookie/crumb fetch failed" and runs slow (about 1 to 2 min per symbol/mode). Chart data still came back. Two stray `HTTP 401 Invalid Crumb` messages were seen (quote-type lookups); no retries were needed.

## OpenBB: could NOT be tested as specified
The installed OpenBB 5.0.0 has no equity router and no yfinance provider (`openbb_yfinance` not installed; `obb.equity` raises AttributeError; providers listed: bls, cboe, cftc, deribit, ecb, eia, famafrench, federal_reserve, finra, fred, imf, jodi, nasdaq, tmx, oecd, sec, congress_gov, usda, us_treasury). The requested call `obb.equity.price.historical("AAPL", start_date="2016-01-04", end_date="2025-12-31", provider="yfinance")` fails with `'App' object has no attribute 'equity'`. Installing `openbb-yfinance` was not permitted (only pyarrow was), so I did not. One attempt each at the providers that expose `equity.historical`:
- cboe: DNS failure (cdn.cboe.com blocked)
- tmx: DNS failure (app-money.tmx.com blocked)
- nasdaq: EmptyDataError (no data returned)

Result: no OpenBB price data, so no OpenBB-vs-yfinance comparison (item 5) and no adjustment-parameter documentation from this install. From memory (UNVERIFIED), the openbb-yfinance extension wraps yfinance and takes an `adjustment` parameter (splits_only default vs splits_and_dividends). If that is right, a default call would return split-only prices and not match the trusted dividend-adjusted series. A reviewer should install `openbb-yfinance` in a throwaway env and rerun.

## yfinance results (37 of 38 symbols had data)
Calls: `yf.Ticker(s).history(start="2016-01-04", end="2026-01-01", auto_adjust=True|False, actions=True)`. Index is tz-aware America/New_York midnight; converted to plain dates (no date shift observed: first/last dates match trusted).

Aggregate over 37 symbols, 92,174 return-days: median |return diff| 0.0023%, median per-symbol p99 0.017%, max 61.5% (AMC), 79 days over 0.5% (99.914% within 0.5%), 807 trusted days missing (all DOW). Level ratio yf/trusted: median 0.99999 at start, 1.00000 at end.
- `auto_adjust=True` Close and `auto_adjust=False` Adj Close gave identical statistics (same series).
- 36 of 37 symbols pass the protocol bar (>=99.5% days within 0.5%, no missing days). DOW fails (807 trusted days missing, 13 days over 0.5%). WBA has no data (see below). On a strict reading the basket as a whole is NOT clean: DOW and WBA fail.
- Level ratio is flat (1.0000 +/- 0.0001) for most symbols. Small drift for SPY (0.9905 at start, 1.0000 at end) and QQQ (1.003): dividend back-propagation differs slightly. Steps at spin-off dates for IBM (0.956 before 2021-11-04), MRK (0.954 before 2021-06-03), MMM (1.0425 before 2024-04-01), HON (1.0009). AMC is 2.93 at start (see below).
- Open/high/low on the adjusted basis: level ratio about 1.0 (same exceptions); open-to-open return diffs over 0.5% on 0 to 14 days per symbol (AMC 63). More days than close because of auction/opening-print differences. See `datasources_ohlcv_detail.csv`.
- Volume: Yahoo/trusted median ratio 0.90 to 0.99 (Yahoo consolidated volume is lower by about 1 to 10%, never above the SIP number at p95). Exceptions: HON 1.8 to 2.0 constant over all years (trusted HON volume looks about half; cause unknown, check trusted side), MMM median 1.06 with p95 1.196 (spin-off factor applied to Yahoo volume).

## Splits (item 3e)
yfinance `Close` with auto_adjust=False is already split-adjusted (only dividends are left unadjusted in Adj Close). Split days: yfinance unadjusted return matched trusted return to within 0.05% on every real split in the window: AAPL 2020-08-31 4:1, NVDA 2021-07-20 4:1 and 2024-06-10 10:1, TSLA 2020-08-31 5:1 and 2022-08-25 3:1, GOOGL 2022-07-18 20:1, AMZN 2022-06-06 20:1, WMT 2024-02-26 3:1, AMC 2023-08-24 1:10 reverse. No wrong splits in yfinance. Trusted implies the same splits except AMC (below). yfinance also records spin-offs in the "Stock Splits" column as fractional ratios (HON 2016-10-03 1.0053, 2018-10-01 1.011, 2018-10-29 1.032, 2025-10-30 1.061; IBM 2021-11-04 1.046; MRK 2021-06-03 1.048; MMM 2024-04-01 1.196). Trusted does not adjust for these.

## Material mismatches (all in `datasources_mismatches.csv`)
79 days over 0.5%; 58 of them fall in 2020-03-09 to 2020-03-19.
1. Mar 2020 (58 days, 25+ symbols, up to 8% e.g. TRV 2020-03-16 trusted -10.7% vs yf -20.8%, trusted close 84.04 vs yf 74.57; CVX 03-17, DIS 03-19, HON 03-19). Pattern: the trusted close on one day is wrong, the next day matches yf, producing offsetting errors on consecutive days. Most likely cause: trusted (Alpaca) daily close on circuit-breaker/extreme-volatility days is not the official closing price. yfinance looks right from my memory of public closes (SPY 03-12 about 248.1 and 03-13 about 269.3 unadjusted) but this is UNVERIFIED. I could not cross-check with the local 5-min files (no rows returned for those dates).
2. TSLA 2020-12-18 (trusted +0.4%, close 219.45; yf +6.0%, close 231.67 = 695/3): S&P 500 inclusion day with a huge closing auction. Trusted close predates the auction. Same cause as item 1.
3. DOW: yf starts 2019-03-20 (when-issued trading of Dow Inc.). Trusted has 2016-01-04 to 2019-03-19 (807 days) that are the predecessor DowDuPont history, then a flat 44.18 close 2019-03-21 to 04-01 (stale fill), then -15.6% on 2019-04-02 (vs yf +5.1%). Cause: spin-off ticker reuse. DOW is not comparable before April 2019 and has no valid pre-2019 history on either side.
4. AMC: (a) 2022-08-22 trusted -5.5% vs yf -42%: APE preferred-unit dividend. Trusted adjusted for it; yfinance did not (this is why the level ratio is 2.93 before that date). (b) 2023-08-23 trusted +38.3% vs yf -23.1%, then next day OK: trusted applies the 1:10 reverse split one day early/shifted (yf and the exchange date is 2023-08-24). Both sources disagree, trusted AMC is wrong around the reverse split.
5. IBM 2021-11-04 (Kyndryl), MRK 2021-06-03 (Organon), MMM 2024-04-01 (Solventum): trusted shows the raw price drop, yfinance adjusts for the spin-off. These are provider-methodology differences, with yfinance the better total-return series. Diffs 4.4 to 4.7%.
6. Others over 0.5%: CSCO 2020-05-29 and 06-01 (about 0.5%), SPY 2016-03-18 and WMT 2020-03-19 / MRK 2020-03-13 (ex-dividend days, 0.5 to 2.6%, mostly the Mar 2020 issue).

WBA (delisted 2025-08-28): trusted has 2427 rows, 2016-01-04 to 2025-08-27. yfinance returns an EMPTY frame (log: "$WBA: possibly delisted; no timezone found"), no exception. A delisted symbol silently disappears from yfinance, so any survivorship-sensitive universe built from it would lose WBA entirely.

## Practical problems
- Slow, noisy: the blocked cookie host makes every call slow (about 80 files took roughly 1 to 2 hours sequentially).
- Silent failure on delisted tickers: empty DataFrame with columns present, no error (also with `raise_errors=False`; I used that flag).
- Column shape differs by mode: auto_adjust=True has no Adj Close; False has both Close (split-adjusted) and Adj Close. Dividends and Stock Splits columns appear because actions=True.
- Timezone: tz-aware ET index; must strip tz to compare. No shifts found.
- Stability (item 6): two identical calls for AAPL and SPY: max |close diff| 7.6e-05 and 2.4e-04 (price units, float noise in adjusted values), volume identical, same row counts. Adjusted history changes whenever a new dividend is paid, so the adjusted series from a later run will drift from this one.
- No NaN OHLC rows and no zero-volume days in any symbol. No rate-limit errors with 1 s pauses, sequential. The fetch script crashed once in the stability step on the empty WBA frame; I fixed the helper and re-ran from cache. The per-run fetch log of the first pass (2026-row drop counts) was lost; the max date check on all cached files is the evidence of no 2026 data.

## Verdict
yfinance (adjusted close returns): accurate for 36 of 37 symbols against the protocol (>=99.5% within 0.5%, no missing days); pooled 99.914%. Fails: DOW (missing 807 days, spin-off), WBA (no data). Most remaining disagreements trace to the trusted data (Mar 2020 closes, TSLA 2020-12-18, AMC reverse split date, DOW pre-2019) or to different spin-off handling, not to yfinance.
OpenBB: not testable in this install (no yfinance provider); verdict "unavailable".

## Reviewer double-checks
1. Confirm trusted-side errors (Mar 2020, TSLA 2020-12-18, AMC 2023-08-23, DOW 2019) against an independent source before editing the trusted dataset.
2. Rerun OpenBB with `openbb-yfinance` installed and document its adjustment default.
3. HON trusted volume looks about half of Yahoo's.
4. The 2020-03 explanation is a hypothesis; 5-min files did not cover those dates when I looked.
