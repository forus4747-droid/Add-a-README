# Step 3.7 — Freqtrade 2026.10 (engine accuracy test)

Worker notes: `reports/notes/freqtrade.md`. Reviewer check: scanned adapters for reference reads (none);
deleted output; re-ran both adapters from scratch (S1 ≈ 5 min); re-ran the checker.

| Strategy | Reference trades | Engine trades | Missing / extra | Mismatches | Largest P&L difference | Result |
|---|---|---|---|---|---|---|
| S1 | 9,304 | 9,304 | 0 / 0 | 0 | $0.0000005 | **PASS (with workarounds)** |
| S2 | 179 | 179 | 0 / 0 | 0 | $0.0000005 | **PASS (with workarounds)** |
| S2, used naively | 179 | **284** | — | — | total $36,505 vs $54,050 | **FAIL** (`results/compare_freqtradenaive_S2.json`) |

P&L is Freqtrade's own (`profit_abs`).

## Problems found
1. **Cannot backtest offline out of the box.** It insists on downloading the market list from a crypto
   exchange. Workaround: replace two ccxt download functions with 30 synthetic "AAPL/USD" markets.
2. **It invents candles for nights, weekends and holidays** (assumes a 24/7 market) and this cannot be
   switched off. With real stock dates the swing strategy traded on Sundays: 284 trades instead of 179 and
   $17,545 less profit — a wrong answer with no warning. Workaround: put the daily bars on a fake gap-free
   calendar and map the dates back.
3. **End-of-test positions are closed at the last candle's OPEN, not close** — worth +$1,395.83 of error on
   the 20 open positions. Workaround: extra closing bar.
4. Whole-share sizing, fees, next-open fills and daylight-saving handling were all exact.
5. Slowest engine tested: ~5 min for S1.

## Verdict
**Exact for what it is built for (crypto, 24/7). Unsafe for stocks unless wrapped:** problem 2 silently
produces wrong results. Its bot features (live running, Telegram, dry-run) are not tested here. For the
final repo: not used as a stock backtester.
