# Step 3.6 — Jesse 3.6.1 (engine accuracy test)

Worker notes: `reports/notes/jesse.md`. Reviewer check: scanned adapters for reference reads (none); deleted
output; re-ran both adapters from scratch; re-ran the checker.

| Strategy | Reference trades | Engine trades | Missing / extra | Mismatches | Largest P&L difference | Result |
|---|---|---|---|---|---|---|
| S1 | 9,304 | 9,304 | 0 / 0 | 0 | $0.0000005 | **PASS (with workarounds)** |
| S2 | 179 | 179 | 0 / 0 | 0 | $0.0000005 | **PASS (with workarounds)** |

P&L is Jesse's own. Runs without database, Redis or network via `jesse.research.backtest`.

## Problems found
1. **Market orders fill at the current candle's close — there is no "next open" mode.** Probe: fill at
   195.885 when the next open was 195.86. For a "decide at close, trade next open" rule this is a small
   look-ahead-free but systematically different price.
2. **Jesse requires 1-minute candles.** Our data is 5-minute. Workaround: each 5-min bar is fed as two
   1-minute rows (a flat "opening print", then the real bar); Jesse's own aggregation then rebuilds the
   original 5-min and daily bars exactly, and orders placed on the opening print fill at the open.
   The price path inside a bar is invented, so this is only valid for market orders at bar opens.
3. **Spot mode deducts the fee from the share count**, which changes position size. Futures mode at 1×
   leverage had to be used to get a plain 0.05% fee on traded value.
4. A naive setup (one row per bar, 5m route) produced 0 trades; cause not investigated (time limit).
5. Slow: ~2 min for S1.

## Verdict
**Exact after heavy workarounds; built for 24/7 crypto, not stocks.** Not recommended for the final repo.
