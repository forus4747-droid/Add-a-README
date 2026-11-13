# Step 3.15 — yfinance 1.7.0 and OpenBB 5.0.0 (data accuracy test) — and a flaw found in our own data

Worker notes: `reports/notes/datasources.md`. Script: `scripts/test_data_sources.py`. Raw: `results/datasources_*.csv`.
No 2026 data was requested or stored (latest date in any file: 2025-12-31).
Reviewer check: the biggest disagreement was traced to the source by the reviewer (below); OpenBB was tested
by the reviewer directly because the worker's rules did not allow installing its yfinance extension.

## yfinance vs our Alpaca daily data (37 symbols, 2016–2025, 92,174 return-days)
| Check | Result |
|---|---|
| Median daily-return difference | 0.0023% |
| Days within 0.5% | 99.914% (79 days outside) |
| Symbols passing the protocol mark | 36 of 37 (DOW fails: ticker has no real history before April 2019) |
| Splits | all 9 real splits in the window handled correctly |
| Delisted stock (WBA) | **returns nothing, with no error** |
| Volume | 1–10% below the consolidated tape |
| Speed here | very slow (a blocked cookie host adds ~1 min per request) |

**Verdict: accurate. Keep as an independent cross-check source.** Weaknesses: silently drops delisted
stocks (survivorship bias), history changes slightly every time a dividend is paid.

## OpenBB (reviewer's test, `provider="yfinance"`, KO and AAPL)
| Symbol | Missing days | Price level vs dividend-adjusted (2016 → 2025) | Days differing > 0.5% |
|---|---|---|---|
| KO | 0 | 1.396 → 1.019 | 42 |
| AAPL | 0 | 1.113 → 1.004 | 4 |

- **As installed, OpenBB has no stock-price function at all**; `openbb-yfinance` and `openbb-equity` had to
  be added. Other providers (Cboe, TMX, Nasdaq) are blocked or returned nothing here.
- **Its default "close" is adjusted for splits but not dividends.** For a dividend payer like KO that
  understates ten-year return by ~28% and puts a fake drop on every ex-dividend day (the 42 days).
  The dividend is supplied in a separate column; nothing warns you.

**Verdict: a thin wrapper over yfinance for prices; adds a trap (dividends) and nothing we need. Not used.**

## The more important finding: our "trusted" Alpaca daily bars contain wrong closes
58 of the 79 disagreements fall in 9–19 March 2020 across 25+ stocks. Reviewer traced one to the source:

| TRV, 2020-03-16 | Value |
|---|---|
| Alpaca daily bar close | **$95.91** |
| Alpaca 1-minute bars: closing auction at 16:01 | $85.10 on 820,820 shares |
| Alpaca 1-minute bars: a trade at 16:07 | $95.91 on **100 shares** |
| Yahoo close | $85.10 |

Alpaca's daily bar takes the last trade of the day — here a stray 100-share late print — not the closing
auction. The worker also flagged TSLA 2020-12-18, AMC's 2023 reverse split (one day off) and several
spin-offs (IBM/Kyndryl, MRK/Organon, MMM/Solventum) that Alpaca does not adjust for.

**Fix (Step 3.17):** `scripts/repair_daily.py` rebuilds every day's official open and close from Alpaca's own
minute bars (the high-volume auction minute) and logs each change. Because the open price is the scoring
target, every skill is re-scored on the repaired data and both sets of numbers are kept.
