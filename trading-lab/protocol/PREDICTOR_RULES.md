# Rules for testing a predictive "skill" (prediction test P)

Goal: take a repo's own prediction method, run it on our data with NO look-ahead, and write its scores to a
file. A separate fixed script does the scoring. You never compute the verdict yourself.

## Output contract
`results/preds/SKILL_swing.parquet` and/or `results/preds/SKILL_day.parquet`, columns exactly:
`symbol, date, score` — date as `YYYY-MM-DD` string; score = higher means "expected to go up more".
- Swing: one row per stock per day t, for every day in 2024-01-01 → 2025-12-31, built ONLY from daily bars
  with date <= t. It will be compared with the return from open[t+1] to open[t+6].
- Day: one row per Dow symbol per day, built ONLY from that day's 5-min bars before 10:00 (09:30–09:55) and
  any earlier days. It will be compared with the return from the 10:00 open to the 15:55 open.
Then run: `PY_CORE scripts/score_skill.py SKILL` — it prints and saves the metrics. Report them unedited.

## You MUST
1. Read `protocol/PROTOCOL.md` (§2 splits, §3 metrics), `lab/data.py`, `lab/score.py` first.
2. Use the repo's OWN method as faithfully as possible (its features, model, default hyper-parameters).
   Cite the repo file/function each piece comes from in `reports/notes/SKILL.md`.
3. Anything that learns from data is fitted on TRAIN only (daily: dates <= 2023-12-31; 5-min: <= 2024-06-30).
   DEV (2024 daily / 2024-H2 5-min) may be used for early stopping or picking among the repo's own documented
   options. VAL (2025) is NEVER used for fitting, tuning, feature selection, scaling statistics, or choosing
   what to report. Run on VAL once.
4. Prove no look-ahead with a truncation test and record it in the notes: recompute scores for 3 random
   (symbol, date) pairs using a copy of the data cut off at that date; they must equal the full-run scores.
5. Put code in `skills/SKILL/` (one runnable entry script `skills/SKILL/run.py`). Write `reports/notes/SKILL.md`:
   what the method is, exact steps, every problem and its fix, truncation-test result, final metrics.

## You MUST NOT
- Use the target, future prices, or anything dated after t when building the score for t. Beware: centred
  rolling windows, `shift(-n)`, normalising with full-sample mean/std, forward-fill from the future, labels
  leaking through qlib-style `Ref($close, -n)` expressions into features.
- Tune on VAL, re-run with different settings after seeing VAL numbers, or report the best of several runs.
  If you must re-run because of a bug, say so and report both results.
- Edit `lab/`, `protocol/`, `scripts/`, `reference/`, `tests/`, or any other skill's files. No git commands.
- Download market data from anywhere. Use only `lab.data`. Installing Python packages the repo needs is
  allowed (note them).
- Invent numbers. If the method cannot be run, say exactly why and stop.
- Spend more than ~45 minutes.

## Final message
Reply with: the metrics table printed by score_skill.py (DEV and VAL), the truncation-test result, the list
of problems found, and anything a reviewer should double-check.
