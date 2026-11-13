# Step 3.1 — vectorbt (engine accuracy test)

Worker: lower-cost model under `protocol/ADAPTER_RULES.md`. Worker notes: `reports/notes/vectorbt.md`.
Reviewer check (done by the lead, independently): scanned adapter code for any read of the reference
(none), deleted the worker's output, re-ran both adapters from scratch, re-ran the checker.

| Strategy | Reference trades | vectorbt trades | Missing / extra | Price, share, time mismatches | Largest P&L difference | Result |
|---|---|---|---|---|---|---|
| S1 | 9,304 | 9,304 | 0 / 0 | 0 | $0.0000005 | **PASS** |
| S2 | 179 | 179 | 0 / 0 | 0 | $0.0000005 | **PASS** |

Raw: `results/compare_vectorbt_S1.json`, `results/compare_vectorbt_S2.json`, `results/trades/vectorbt_*.csv`.

## Problems found
1. **Rule wording ambiguity (ours, not vectorbt's).** The worker first limited the stop to 10:00–15:40 and got
   22 wrong exits. STRATEGIES.md rule 3 now states the stop window explicitly. Fixed in the protocol text.
2. **vectorbt has no "close at end of window" order.** Workaround: one extra row priced at the last close with
   an exit signal. Result identical to reference.
3. **vectorbt does not track strategy state.** "One trade per day" and "stop only while long" had to be encoded
   in the signal arrays with pandas; vectorbt only does fills, sizing, fees and P&L. Those it does exactly.

## Verdict
**Good skill — keep.** Fills, share counts, fees and P&L are exact to the cent on 9,483 trades, and it is the
fastest engine tried. Weakness to remember: stateful rules must be written outside the engine, which is where
mistakes can creep in (as problem 1 showed).
