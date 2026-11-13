# Step 3.17 — Repairing stray closing prices in our own daily data

Trigger: Step 3.15 showed Alpaca's daily bar sometimes takes its close from a stray late trade instead of
the closing auction (TRV 2020-03-16: $95.91 on 100 shares vs the real $85.10 on 820,820 shares).

Scripts: `scripts/repair_daily.py` (downloads the 09:30–09:34 and 15:58–16:04 one-minute bars for all 521
symbols on all 2,514 days → `daily/auction_prices.parquet`), `scripts/repair_daily_apply.py` (applies the rule
→ `daily/daily_v2.parquet`). Every change: `results/03_17_daily_close_repairs.csv`.

## Three attempts — the first two were wrong and were caught by validation
| Rule | Values changed | Check against Yahoo (36 symbols, 92k days): days disagreeing > 0.5% | Outcome |
|---|---|---|---|
| none (original data) | 0 | closes 79 · opens 208 | baseline |
| v1: replace if daily differs from auction-minute price by > 0.5% | 86,325 | — | **wrong.** Some stocks (GSK, BP…) were "repaired" nearly every day: minute and daily bars carry different dividend-adjustment scales. |
| v2: compare with each stock's own 21-day typical ratio | 36,478 (35,098 opens) | closes 164 · opens 1,364 | **wrong.** Made agreement with Yahoo worse. The first-minute average is not the opening price for volatile stocks; Alpaca's daily opens were already right. |
| **v3 (adopted): closes only, auction minute must hold ≥ 3% of the day's volume** | **418** | **closes 49** · opens 208 (untouched) | better than the original; remaining 49 are spin-offs and AMC's share events, which no price rule can fix |

## What changed
- 418 closing prices out of 1,259,107 (0.03%), 191 of them in 2020. Median change 1.0%, largest 23.7%.
- **No opening price changed.** Since every prediction is scored on open-to-open returns, **no score in
  Steps 2–3.13 changes** (re-ran baselines and Qlib after the switch: identical to four decimals).
- `lab.data.load_daily()` now reads the repaired file. The original is kept as `daily/daily.parquet`.

## Still wrong in the data (documented, not fixable by rule)
Spin-offs Alpaca does not adjust for (IBM 2021-11-04, MRK 2021-06-03, MMM 2024-04-01), AMC's 2022 special
dividend and 2023 reverse split (one day off), DOW's pre-2019 predecessor history. All sit in single stocks on
single days; rank-based scoring and ±50% target clipping limit their effect.

## Lesson for the final repo
A data fix must be validated against an independent source before it is trusted. Two plausible-looking
repairs here would have damaged 36,000–86,000 good values.
