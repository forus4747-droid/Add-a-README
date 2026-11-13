# Step 3.9 — zipline-reloaded (engine accuracy test)

Worker notes: `reports/notes/zipline.md`. Reviewer check: scanned adapters for reference reads (none);
deleted output; re-ran both adapters from scratch; re-ran the checker.

| Strategy | Reference trades | Engine trades | Missing / extra | Mismatches | Largest P&L difference | Result |
|---|---|---|---|---|---|---|
| S1 | 9,304 | 9,304 | 0 / 0 | 0 | $0.0000005 | **PASS (with heavy workarounds)** |
| S2 | 179 | 179 | 0 / 0 | 0 | $0.0000005 | **PASS (with workarounds)** |

## Problems found
1. **No built-in way to fill at the next bar's open.** Every built-in fill model uses the bar's CLOSE: a
   daily order placed on day t fills at day t+1's close. A custom fill class had to be written.
2. **Orders are sized from the previous close**, not the fill price; fill-time sizing had to be put inside
   the custom fill class.
3. **Minute prices are stored rounded to 3 decimals** — 777 entry prices were wrong until the writer was replaced.
4. **Only 1-minute bars are supported intraday**; 5-minute data had to be mapped into 1-minute slots.
5. **Half-day sessions:** the exchange calendar drops bars our data contains (5 missing, 1 extra trade) —
   needed a custom calendar.
6. **Zero-volume bars are silently skipped for fills** (matters for the end-of-test closing bar).
7. No per-trade net P&L; computed from the engine's fills (totals agree with the engine's portfolio value to 1e-5).
8. Slowest to get working of all engines (worker needed 47 steps; others 7–28).

## Verdict
**Exact only after replacing its fill model, its price writer and its calendar.** Out of the box it trades at
different prices than the strategy intends. Its pipeline/factor tooling was not tested. Not used as an
engine in the final repo.
