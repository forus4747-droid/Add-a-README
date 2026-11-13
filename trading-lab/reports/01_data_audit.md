# Step 1 — Data audit

Script: `scripts/audit_data.py`. Raw output: `results/01_audit.json`, `results/01_audit_5min.csv`,
`results/01_audit_daily_big_moves.csv`. File hashes: `reports/01_data_manifest.csv`.

## 5-minute set (30 Dow stocks)
| Check | Result |
|---|---|
| Files / bars | 90 files, 1,411,148 bars |
| Last date | 2025-12-31 (script asserts no 2026 data is present) |
| Duplicate timestamps | 0 |
| Missing values | 0 |
| Impossible bars (high < low, price <= 0) | 0 |
| Zero-volume bars | 0 |
| Days with fewer than 78 bars | 211 symbol-days (market half-days + thin bars). S1 skips these days by rule. |
| Largest single 5-min move | 6.7% (WBA, 2024) — plausible, kept |

## Daily set (521 symbols, 2016-01-04 → 2025-12-31)
| Check | Result |
|---|---|
| Rows / symbols | 1,259,107 rows, 521 symbols (500 by 2022-H2 dollar volume ∪ 20 ETFs ∪ 30 Dow) |
| Symbols with history back to Jan 2016 | 462 (the rest listed later, e.g. IPOs) |
| Duplicates / missing values / impossible bars | 0 / 0 / 0 |
| One-day moves over 50% | 67 (list in results file) |

## Problems found and how they are handled
1. **67 daily moves over ±50%.** Most are real (AMC 2021, biotech news). At least one is an adjustment
   artifact: AA 2016-11-01 −73% is the Alcoa/Arconic spin-off, not a real loss. All are before or inside
   TRAIN except a few real ones. *Handling:* targets are clipped to ±50% when fitting models; scoring uses
   rank-based metrics, which a single outlier cannot distort.
2. **Survivorship.** Universe drawn from today's listings (see PROTOCOL §1). Not fixable with the data
   sources available; affects all repos equally.
3. **5-min vs daily closes differ slightly.** Daily return built from the last 5-min bar vs the official
   daily bar: median difference 0.02–0.07%, 99th percentile 0.3–1.0%. Cause: the official close is the
   closing auction at 16:00, the last 5-min bar close is the last trade before it; plus the daily set is
   dividend-adjusted. *Handling:* each test uses one set only; never mixed.

Verdict: data is clean enough to proceed.
