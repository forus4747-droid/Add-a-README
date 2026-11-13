# Step 3.13 — Freqtrade bundled strategies: buy/sell signals (prediction test)

Worker notes: `reports/notes/ftsample.md`. Code: `skills/ftsample/`. Signals come from the strategy classes'
own `populate_*` methods at default parameters. Reviewer check: re-ran the fixed signal scorer (same numbers);
worker's truncation test 12 of 12.

Rules: `SampleStrategy` = buy when RSI crosses up through 30 (with TEMA/Bollinger guards), sell when RSI
crosses up through 70. `minimal` template = the same RSI crossings without guards. (`full` template renders
to rules identical to SampleStrategy.)

## VAL 2025 — return after a signal, minus the average stock over the same time
| Rules | Data | Side | Signals | Excess after signal | t-stat | Verdict |
|---|---|---|---|---|---|---|
| SampleStrategy | 5-min, Dow 30 | buy | 5,002 | −0.010% | −0.04 | no proven edge |
| SampleStrategy | 5-min, Dow 30 | sell | 134 | −0.162% | −1.66 | no proven edge |
| SampleStrategy | daily, 501 stocks | buy | 962 | +0.220% | 0.44 | no proven edge |
| minimal | 5-min, Dow 30 | buy | 7,770 | −0.017% | 0.15 | no proven edge |
| minimal | 5-min, Dow 30 | sell | 8,372 | +0.007% | 0.61 | no proven edge |
| minimal | daily, 501 stocks | buy | 1,490 | +0.187% | 0.29 | no proven edge |
| minimal | daily, 501 stocks | sell | 2,094 | −0.358% | −1.20 | no proven edge |

Raw: `results/signals_ft*.csv` (includes DEV).

## Problems found
1. **The buy signal's edge on 5-minute bars is zero to four decimals** against a 0.1% round-trip cost.
2. **SampleStrategy's sell rule almost never fires** on stocks (4.5 times per symbol-year on 5-min bars,
   0.05 on daily) — positions would rely entirely on the stop-loss/ROI table, not tested here.
3. The strategy is documented by Freqtrade itself as an example, not a profitable system — the test confirms it.

## Verdict
**No predictive skill. Not carried forward.**
