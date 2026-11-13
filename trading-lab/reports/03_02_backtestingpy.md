# Step 3.2 — backtesting.py v0.6.6 (engine accuracy test)

Worker notes with source citations: `reports/notes/backtestingpy.md`. Reviewer check: scanned adapters for
any read of the reference (none), deleted output, re-ran both adapters from scratch, re-ran the checker.

| Strategy | Reference trades | Engine trades | Missing / extra | Mismatches | Largest P&L difference | Result |
|---|---|---|---|---|---|---|
| S1 | 9,304 | 9,304 | 0 / 0 | 0 | $0.0000005 | **PASS (with workarounds)** |
| S2 | 179 | 179 | 0 / 0 | 0 | $0.0000005 | **PASS (with workarounds)** |

## Problems found — the engine is exact only after three workarounds
1. **Share count is fixed before the fill price is known.** `buy(size=N)` sizes at order time. To get
   `floor(10000 / next open)` the adapter passes a fraction-of-equity size so the engine sizes at fill time.
   A first attempt was 1 share short on 6 trades where 10000/price is a whole number; fixed with a 1e-12 nudge.
2. **Commission silently shrinks position size.** With a plain `commission=0.0005` the engine buys
   `floor(10000 / (price × 1.0005))` shares — fewer than asked. Workaround: a commission function that
   returns 0 during the sizing call.
3. **End-of-test positions are closed at the last bar's OPEN, not its close** (`finalize_trades=True`).
   On S2 this alone changed 21 exits and total P&L from $54,050 to $55,374 (+2.4% error). Workaround: extra
   closing bar. The worker flagged that this needed an exit-date remap beyond "timestamp reformatting";
   reviewer accepts it because the engine still produced the fill and the price, and it is disclosed here.
4. Same rule-wording misread as vectorbt (22 exits) — our wording, already fixed in STRATEGIES.md.

## Verdict
**Usable, but its defaults mislead.** The arithmetic is exact once configured, yet an ordinary user following
the docs would get different share counts (problem 2) and a different final P&L (problem 3) without any
warning. For the final repo: keep only behind a wrapper that applies these three fixes, or prefer vectorbt.
