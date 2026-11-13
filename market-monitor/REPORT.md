# Market monitor report (as of 2026-11-12)

Generated 2026-11-13T18:45:11+00:00 UTC. S&P 500 last close 7592.40. This is a statistical history check, not investment advice; every probability below is a historical frequency adjusted by simple models, and the models have only weak out-of-sample skill (see the skill columns).

## Data status

25 of 25 sources downloaded. FRED reachable: yes.

CAUTION: the Shiller file's last valid CAPE input is 2023-09. Since then the earnings base is held constant (in real terms), so today's CAPE is an estimate and probably reads a little high if real earnings kept growing.

Note: CPI for 2025-10 was not published and is log-interpolated.

The latest feature row is a partial month (2026-11) using the last close.

## Where the market stands

| Measure | Value | Percentile of own history |
|---|---|---|
| cape | 47.2 | 100% |
| cape_pct | 99.7% | 96% |
| infl_yoy | 3.95% | 70% |
| infl_chg_12m | 1.09 pt | 66% |
| rate10 | 5.10% | 77% |
| rate10_chg_12m | 1.09 pt | 94% |
| ecy | 0.4% | 8% |
| mom_12m | 10.8% | 57% |
| trend_10m | 3.0% | 50% |
| dd_now | -2.9% | 77% |
| rv_3m | 14.6% | 61% |
| curve | 0.98 pt | 32% |
| bill_chg_12m | 0.43 pt | 70% |
| credit_spread | 0.47 pt | 4% |
| credit_spread_chg_12m | -0.13 pt | 36% |
| unemp_gap | 0.00 pt | 38% |

## Probabilities for the S&P 500

`base` is the historical frequency; `final` blends in the analog and regression models using weight w (0 = ignore models). Skill is Brier skill versus the base rate (positive = better than just quoting the base rate).

| Question | Base | Analog | Logit | Final | w live | Skill 1950-99 | Skill 2000-now (holdout) |
|---|---|---|---|---|---|---|---|
| S&P 500 closes lower 21 trading days (about 1 month) from now | 39.6% | 28.3% | 42.6% | 37.5% | 0.50 | 0.002 | 0.003 |
| S&P 500 closes at least 5% below today's close at some point in the next 21 trading days | 18.2% | 6.7% | 20.0% | 13.3% | 1.00 | 0.095 | 0.053 |
| S&P 500 closes lower 63 trading days (about 3 months) from now | 35.8% | 25.0% | 38.1% | 33.7% | 0.50 | 0.019 | 0.002 |
| S&P 500 closes at least 10% below today's close at some point in the next 63 trading days | 14.9% | 8.3% | 18.7% | 13.5% | 1.00 | 0.171 | 0.031 |
| S&P 500 closes lower 252 trading days (about 12 months) from now | 30.4% | 21.7% | 36.8% | 30.4% | 0.00 | 0.010 | -0.025 |
| S&P 500 closes at least 10% below today's close at some point in the next 252 trading days | 36.7% | 31.7% | 45.7% | 37.7% | 0.50 | 0.059 | -0.056 |
| S&P 500 closes at least 20% below today's close at some point in the next 252 trading days | 17.2% | 3.3% | 22.8% | 15.1% | 0.50 | 0.088 | -0.051 |

## Closest historical analogs

Months whose valuation, inflation, rates, momentum, trend, volatility and drawdown looked most like today.

| Period | Months | Avg distance | Avg next-12m return | Worst drawdown in next 12m |
|---|---|---|---|---|
| 1968-04 to 1968-06 | 3 | 0.61 | -1.9% | -10.1% |
| 2018-05 to 2018-07 | 3 | 0.74 | 5.2% | -16.5% |
| 1999-11 to 2000-02 | 2 | 0.76 | -6.5% | -9.3% |
| 1996-08 to 1996-09 | 2 | 0.77 | 38.3% | -0.4% |
| 2006-06 to 2006-08 | 2 | 0.77 | 17.1% | -2.8% |
| 1997-03 to 1997-03 | 1 | 0.78 | 44.4% | -2.6% |
| 2013-08 to 2013-08 | 1 | 0.78 | 22.6% | 0.0% |
| 2018-11 to 2018-11 | 1 | 0.87 | 12.1% | -14.8% |

## Ten-year outlook from valuation

CAPE 47.2 (estimate) implies an annualised real return of about -1.2% per year over ten years, with a one-standard-deviation band of -5.5% to 3.2% (regression R-squared 0.29, in-sample, 1587 overlapping months).

## Signals board (5 vulnerability and 0 trigger rules ON)

| Rule | Type | State | Current value | Months ON | P(20% drop within 12m) when ON | when OFF | History starts |
|---|---|---|---|---|---|---|---|
| valuation | vulnerability | ON | 0.997 | 494 | 21.5% | 14.8% | 1881-04 |
| tightening | vulnerability | ON | 0.431 | 494 | 11.2% | 21.3% | 1882-01 |
| inflation_reaccelerating | vulnerability | ON | 3.950 | 448 | 26.5% | 14.1% | 1883-02 |
| oil_shock | vulnerability | ON | 0.528 | 47 | 16.7% | 9.0% | 2008-07 |
| leader_crack | vulnerability | ON | -0.305 | 0 | n/a | n/a | current only |
| narrow_market | vulnerability | OFF | 0.059 | 47 | 7.1% | 13.4% | 2004-05 |
| trend_break | trigger | OFF | 0.030 | 627 | 28.0% | 12.0% | 1881-10 |
| credit_stress | trigger | OFF | -0.022 | 24 | 16.7% | 11.7% | 2008-03 |
| volatility_regime | trigger | OFF | 18.700 | 33 | 21.2% | 13.1% | 1990-01 |
| curve_inverted | trigger | OFF | 0.975 | 100 | 26.0% | 12.6% | 1934-01 |

## Past drawdowns of 19.9% or more (daily closes)

| Peak | Trough | Depth | Days to trough | Recovered | CAPE at peak | Rallies >=10% / >=20% |
|---|---|---|---|---|---|---|
| 1929-09-16 | 1932-06-01 | -86.2% | 989 | 1954-09-22 | 33.6 | 10 / 4 |
| 1956-08-03 | 1957-10-22 | -21.5% | 445 | 1958-09-24 | 19.5 | 1 / 0 |
| 1961-12-12 | 1962-06-26 | -28.0% | 196 | 1963-09-03 | 22.4 | 0 / 0 |
| 1966-02-09 | 1966-10-07 | -22.2% | 240 | 1967-05-04 | 24.3 | 0 / 0 |
| 1968-11-29 | 1970-05-26 | -36.1% | 543 | 1972-03-06 | 23.2 | 0 / 0 |
| 1973-01-11 | 1974-10-03 | -48.2% | 630 | 1980-07-17 | 19.1 | 2 / 0 |
| 1980-11-28 | 1982-08-12 | -27.1% | 622 | 1982-11-03 | 10.1 | 2 / 0 |
| 1987-08-25 | 1987-12-04 | -33.5% | 101 | 1989-07-26 | 18.7 | 2 / 0 |
| 1990-07-16 | 1990-10-11 | -19.9% | 87 | 1991-02-13 | 18.2 | 0 / 0 |
| 2000-03-24 | 2002-10-09 | -49.1% | 929 | 2007-05-30 | 46.8 | 4 / 2 |
| 2007-10-09 | 2009-03-09 | -56.8% | 517 | 2013-03-28 | 28.2 | 4 / 1 |
| 2020-02-19 | 2020-03-23 | -33.9% | 33 | 2020-08-18 | 32.4 | 0 / 0 |
| 2022-01-03 | 2022-10-12 | -25.4% | 282 | 2024-01-19 | 39.7 | 2 / 0 |

## What followed the first close 20%, 30%, 40% below a peak

| Threshold | Peak | Hit date | 1y | 3y | 5y | Further fall to final low | Days later |
|---|---|---|---|---|---|---|---|
| 20% | 1929-09-16 | 1929-10-28 | -25.5% | -71.5% | -59.8% | -80.7% | 947 |
| 20% | 1956-08-03 | 1957-10-21 | 31.0% | 38.6% | 40.4% | -0.4% | 1 |
| 20% | 1961-12-12 | 1962-05-28 | 26.1% | 59.3% | 63.0% | -5.7% | 29 |
| 20% | 1966-02-09 | 1966-08-29 | 24.6% | 25.5% | 34.2% | -1.8% | 39 |
| 20% | 1968-11-29 | 1970-01-29 | 10.7% | 35.9% | -14.8% | -19.1% | 117 |
| 20% | 1973-01-11 | 1973-11-27 | -28.1% | 6.5% | -0.7% | -34.9% | 310 |
| 20% | 1980-11-28 | 1982-02-22 | 32.1% | 63.5% | 150.6% | -8.2% | 171 |
| 20% | 1987-08-25 | 1987-10-19 | 22.9% | 34.9% | 81.2% | -0.4% | 46 |
| 20% | 2000-03-24 | 2001-03-12 | -1.2% | -4.8% | 10.8% | -34.2% | 576 |
| 20% | 2007-10-09 | 2008-07-09 | -29.1% | 8.0% | 34.6% | -45.6% | 243 |
| 20% | 2020-02-19 | 2020-03-12 | 59.0% | 58.0% | 126.3% | -9.8% | 11 |
| 20% | 2022-01-03 | 2022-06-13 | 16.6% | 59.5% | n/a | -4.6% | 121 |
| 30% | 1929-09-16 | 1929-10-29 | -16.2% | -66.3% | -54.6% | -78.5% | 946 |
| 30% | 1968-11-29 | 1970-05-14 | 36.4% | 43.4% | 20.0% | -8.2% | 12 |
| 30% | 1973-01-11 | 1974-07-05 | 12.8% | 20.1% | 23.0% | -25.6% | 90 |
| 30% | 1987-08-25 | 1987-10-19 | 22.9% | 34.9% | 81.2% | -0.4% | 46 |
| 30% | 2000-03-24 | 2001-09-17 | -15.9% | 8.6% | 27.2% | -25.2% | 387 |
| 30% | 2007-10-09 | 2008-10-06 | -0.2% | 8.2% | 56.6% | -36.0% | 154 |
| 30% | 2020-02-19 | 2020-03-20 | 71.0% | 70.8% | 147.8% | -2.9% | 3 |
| 40% | 1929-09-16 | 1929-11-12 | -9.8% | -61.8% | -49.1% | -76.5% | 932 |
| 40% | 1973-01-11 | 1974-08-23 | 17.8% | 36.7% | 52.1% | -13.0% | 41 |
| 40% | 2000-03-24 | 2002-07-16 | 10.3% | 36.3% | 71.6% | -13.8% | 85 |
| 40% | 2007-10-09 | 2008-10-09 | 17.8% | 31.3% | 87.2% | -25.6% | 151 |

## Live scorecard

7 predictions issued, 0 resolved, 7 pending. Nothing has resolved yet, so there is no live skill estimate.

Ledger check: ok: 7 predictions, 0 resolutions.

## Market snapshot

| Symbol | Last close | Date | Year to date | From 52-week high (closes) |
|---|---|---|---|---|
| ^GSPC | 7592.40 | 2026-11-12 | 10.9% | -2.9% |
| ^IXIC | 25366.09 | 2026-11-12 | 9.1% | -8.1% |
| NVDA | 166.19 | 2026-11-12 | -10.9% | -30.5% |
| GOOG | 295.35 | 2026-11-12 | -5.9% | -26.0% |
| XEQT.TO | 45.58 | 2026-11-12 | 14.3% | -1.7% |
| ^GSPTSE | 36137.20 | 2026-11-12 | 14.0% | -2.2% |
| CAD=X | 1.42 | 2026-11-12 | 4.0% | -0.2% |
| ^TNX | 5.10 | 2026-11-12 | 22.6% | -3.9% |
| ^IRX | 4.13 | 2026-11-12 | 16.4% | 0.0% |
| ^VIX | 18.70 | 2026-11-12 | 25.1% | -39.8% |
| HYG | 76.98 | 2026-11-12 | -4.5% | -5.2% |
| BZ=F | 95.82 | 2026-11-12 | 57.5% | -19.0% |
| GC=F | 3885.30 | 2026-11-12 | -10.5% | -26.9% |
| DX-Y.NYB | 103.17 | 2026-11-12 | 5.0% | 0.0% |
| BTC-USD | 71342.97 | 2026-11-12 | -18.5% | -28.4% |

## Accepted news (last 10 days)

None accepted.
