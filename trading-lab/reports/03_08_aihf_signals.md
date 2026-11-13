# Step 3.8 — ai-hedge-fund rule-based technical signals (prediction test)

Source tested: `src/agents/technicals.py` at commit `6c41ae8` (2026-07-31), the last commit before the
repo's v2 rebuild deleted it. The current v2 repo contains only LLM persona agents, which are excluded
(PROTOCOL §2). Worker notes: `reports/notes/aihf.md`. Code: `skills/aihf/`.

Reviewer check: (1) every copied function compared with the source by syntax tree — all 13 identical;
(2) no use of targets or negative shifts in the skill code; (3) own truncation test, different random seed —
5 of 5 scores recomputed from data cut at the date match the file exactly (worker: 300 of 300);
(4) Hurst bug reproduced independently (below). Scores from `scripts/score_skill.py`, files `results/score_aihf_*.csv`.

## Result on VAL (2025, 501 stocks, 244 days)
| Signal | Rank IC | t-stat | Hit rate | Top-quintile net/yr | Equal-weight/yr | Verdict |
|---|---|---|---|---|---|---|
| Combined (repo's weights) | 0.0038 | 0.23 | 50.5% | 23.7% | 18.7% | no proven edge |
| Trend (EMA + ADX) | 0.0002 | 0.01 | 50.4% | 17.3% | 18.7% | no proven edge |
| Mean reversion (z-score, Bollinger, RSI) | 0.0050 | 0.36 | 50.1% | 28.4% | 18.7% | no proven edge |
| Momentum (1/3/6-month) | −0.0028 | −0.18 | 50.2% | 16.6% | 18.7% | no proven edge |
| Volatility regime | −0.0032 | −0.28 | 50.1% | 11.2% | 18.7% | no proven edge |
| Stat-arb (Hurst + skew) | — | — | — | — | — | not scorable (see 2) |

Every rank IC is indistinguishable from the random baseline (IC 0.000, Step 2). The two positive excess
returns come with t-stats of 0.2–0.4: luck-sized, not evidence.

## Problems found
1. **Bug in the repo: the Hurst exponent is always ~0.** `calculate_hurst_exponent` subtracts two pandas
   Series that share index labels, so every "lagged difference" is zero. Reproduced by the reviewer: AAPL, KO
   and AMC all return exactly 4.687e-16. The stat-arb signal's "is the price mean-reverting?" test is
   therefore always true; the signal collapses to "63-day skew > 1 → bullish".
2. **Second flaw in the same function:** even with the subtraction fixed, it takes `sqrt(std)`, which halves
   the exponent (≈0.22–0.27 for ordinary stocks), so its `H < 0.4` test would still be true for almost
   everything.
3. The stat-arb score takes only three values (−1, 0, +1), so rank metrics cannot be computed. Recorded as
   "not scorable", not as "no edge".
4. `calculate_adx` modifies the DataFrame passed to it (side effect).

## Verdict
**No predictive skill found. Do not carry forward as-is.** Reusable pieces: the indicator helpers (EMA, RSI,
Bollinger, ADX, ATR) are standard and can be checked against TA-Lib in the indicator test. The Hurst function
must be rewritten before any use.

## Addendum — stat-arb signal scored with the discrete-signal scorer
`scripts/score_signals.py aihf_statarb swing` → `results/signals_aihf_statarb_swing.csv` (table in that file).
