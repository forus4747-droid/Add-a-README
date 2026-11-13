# Step 3.4 — Backtrader (engine accuracy test)

Worker notes: `reports/notes/backtrader.md`. Reviewer check: scanned adapters for reference reads and for
future-bar indexing (`[1]`) — none; deleted output; re-ran both adapters from scratch; re-ran the checker.

| Strategy | Reference trades | Engine trades | Missing / extra | Mismatches | Largest P&L difference | Result |
|---|---|---|---|---|---|---|
| S1 | 9,304 | 9,304 | 0 / 0 | 0 | $0.0000005 | **PASS** |
| S2 | 179 | 179 | 0 / 0 | 0 | $0.0000005 | **PASS** |

P&L is Backtrader's own (`trade.pnlcomm`), no recomputation.

## Problems found
1. **Indicator values shift by one bar inside `next_open`.** There `sma[0]` is still yesterday's value.
   Written the natural way, every S2 entry was one day late. Easy to get wrong, no warning.
2. **`set_coc(True)` makes ALL market orders fill at the close**, not only the ones intended. Needed a
   per-order opt-out.
3. **An order placed on the last bar is silently dropped** (no next bar to fill on) — 21 open positions
   never closed, so their P&L was missing from the results. Workaround: close inside `next_open` of the last
   bar with cheat-on-close.
4. To size on the fill bar's open, `cheat_on_open=True` is required. It is legitimate here (signal uses only
   earlier bars) but the same switch makes look-ahead mistakes easy.
5. Slow: S1 takes ~2 min 45 s (vectorbt: seconds; vn.py: 11 s).
6. Same rule-wording misread (22 exits) — ours, already fixed.

## Verdict
**Accurate, own accounting exact, but slow and full of timing traps.** Three of the problems silently
produce wrong results (late entries, dropped final trades). Project is no longer actively developed.
Keep as a cross-check engine only.
