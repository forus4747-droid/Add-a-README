# Step 3.3 — NautilusTrader (engine accuracy test)

Worker notes: `reports/notes/nautilus.md`. Reviewer check: scanned adapters for any read of the reference
(none), deleted output, re-ran both adapters from scratch with the nautilus env, re-ran the checker.

| Strategy | Reference trades | Engine trades | Missing / extra | Mismatches | Largest P&L difference | Result |
|---|---|---|---|---|---|---|
| S1 | 9,304 | 9,304 | 0 / 0 | 0 | $0.0000005 | **PASS (fills exact; P&L recomputed, see 4)** |
| S2 | 179 | 179 | 0 / 0 | 0 | $0.0000005 | **PASS (same)** |

## Problems found
1. **With bar data, a market order fills at the SAME bar's close, not the next bar's open** (worker
   confirmed with a 3-bar test, `bar_execution=True`). That is a look-ahead-prone default for a "decide on
   close, trade next open" strategy. Workaround: feed the venue a quote at each bar's open and submit orders
   there; bars are used for signals only.
2. **Prices were silently rounded to 2 decimals.** The data has sub-cent prices (e.g. 187.845); with
   price precision 2, 2,803 entry prices were wrong. Fixed by setting instrument precision to 6.
3. pandas 3 datetime → integer conversion gives microseconds, Nautilus needs nanoseconds. Adapter bug, fixed.
4. **The engine rounds commission and realised P&L to whole cents per fill.** Its own P&L therefore differs
   from exact arithmetic by up to ~$0.015 per trade. The CSV's `pnl_net` is computed from the engine's fill
   prices and share counts with the protocol fee formula (allowed by ADAPTER_RULES and disclosed). The
   engine's own cent-rounded figure is realistic for a real broker, just not identical to exact maths.
5. Same rule-wording misread (22 exits) — our wording, already fixed.

## Verdict
**Accurate but demanding.** Fill prices, share counts and timestamps are exact on all 9,483 trades once
configured. It is the most realistic engine (real order objects, venue simulation) and the most work: three
of five problems were configuration traps that silently change results. Keep for final-stage realism checks
and anything headed to live trading; not the tool for quick research.
