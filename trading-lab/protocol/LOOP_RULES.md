# Rules for one iteration of the find-mistake / fix loop (Phase 2)

Read `protocol/PROTOCOL_V3_LONG.md` and `lab/long.py` first. They are binding.

## Your data
`lab.long.load_panel()` and `lab.long.load_market()` — daily data 1990-01-02 → 2012-12-31 ONLY. Later data
does not exist in your data root. Do not look for it, download it, or use any other data source or any
knowledge of what markets did after 2012. Rows with `in_univ == True` are the stocks to score that day
(top 1,000 by trailing dollar volume); other rows are history you may use as lookback.

## What you produce
`skills_long/NAME.py` with `predict(panel, market) -> DataFrame[symbol, date, score]`: one row per
in-universe (symbol, date); higher score = expected higher return from open[t+1] to open[t+6].
(For the risk task: `predict_abs(panel, market)`; higher = expected larger |return|.)

## Hard requirements
1. **Causal:** the score for date t uses only rows dated <= t. Must pass
   `PY scripts/score_long.py NAME LOOP --causal` (truncation test) — "causal check: (True, ...)".
2. **Walk-forward fitting:** if anything is learned from data (model weights, IC-weights, thresholds chosen
   by performance, selected features), it must be re-learned for each year Y from labels known before
   Y-01-01 (`lab.long.walk_forward` does this). A threshold or weight you pick by looking at 1991–2012
   results and then hard-code is NOT walk-forward: it is allowed only if you say so explicitly and count it
   in "choices made by looking at results" (keep that count small; every such choice weakens the evidence).
3. **Deterministic:** fixed seeds; two runs give identical scores.
4. **Reasonable cost:** `predict` must run in under ~15 minutes and under ~6 GB of memory on 4 cores (other
   jobs share the machine: use float32, avoid giant intermediate frames, LightGBM `n_jobs=2`).
5. Measure only with `PY scripts/score_long.py NAME LOOP [--diagnose]`. Do not edit `lab/`, `scripts/`,
   `protocol/`, other skills, or anything outside `skills_long/NAME*.py` and `reports/notes/P2_NAME.md`.
   No git. No network.

## Method for the iteration
1. Run the diagnostics on the current best version and read where it is weak or wrong (by year, regime,
   volatility, liquidity, score decile). You may write extra diagnostics of your own.
2. State your hypothesis about the mistake pattern BEFORE building the fix, in the notes.
3. Build the fix. Compare with the current best on LOOP: per-year IC table, pooled summary, and the
   stability across the three sub-periods 1991–1998, 1999–2005, 2006–2012 (an improvement that exists in
   only one sub-period is suspect). **Pay special attention to 2006–2012**: the reviewer will test on later
   years, and signals have been decaying over time.
4. Try at most 6 variants in total. Report ALL of them with their numbers, not only the best. Pick the
   one you would stake on for unseen later years and say why — the most robust, not the highest number.

## Notes file `reports/notes/P2_NAME.md`
Hypothesis; what was built (exact formulas / features / model); every variant tried with LOOP numbers;
choices made by looking at results (count them); causal-check output; runtime; risks a reviewer should probe.

## Final message
The chosen version's name, its LOOP pooled summary and sub-period ICs next to the current best's, the
list of variants tried, the count of result-driven choices, and what could make it fail after 2012.
