# Step 3.11 — FinRL: PPO and A2C agents on the Dow 30 (prediction test)

Worker notes: `reports/notes/finrl.md`. Code: `skills/finrl/`. Reviewer check: re-ran the fixed scorer (same
numbers); worker's truncation test (3 dates, action difference 0.0, `results/finrl_truncation.json`).

Setup: FinRL's standard tutorial pipeline, default indicators and hyper-parameters, 29 Dow stocks (WBA
dropped: delisted), trained 2016–2023, 50,000 steps each, one run, FinRL's default 0.1% cost per side.

| Agent | Split | Rank IC | t-stat | Hit rate | Agent's own account | Equal-weight buy & hold |
|---|---|---|---|---|---|---|
| PPO | DEV 2024 | −0.011 | −0.40 | 50.2% | +0.19% | +14.18% |
| PPO | VAL 2025 | 0.032 | 1.28 | 50.9% | +5.39% | +16.56% |
| A2C | DEV 2024 | −0.060 | −2.08 | 47.4% | −0.11% | +14.18% |
| A2C | VAL 2025 | −0.042 | −1.36 | 47.6% | −0.12% | +16.56% |

Raw: `results/score_finrl_*.csv`, `results/finrl_account_values.csv`.

## Problems found
1. **Both agents badly trail simply holding the stocks** (by 11–14 points a year). They mostly sit in cash.
2. **A2C's choices are slightly worse than random** in both years (negative IC both times).
3. **FinRL fills trades at the same day's close it just observed** — an optimistic assumption a real trader
   cannot get. Its own account numbers are therefore, if anything, flattering.
4. The default "turbulence" switch dumped all positions on 62 days.
5. FinRL's prediction helper throws away the agents' raw actions; a custom loop was needed to record them.
6. Result is from one modest training run; RL results vary a lot run to run (itself a reliability problem).

## Verdict
**No predictive skill; do not carry forward.** Nothing reusable for the final repo beyond the lesson that
the fill-at-observed-close assumption must be avoided.
