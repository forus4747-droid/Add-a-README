# Step 5 — The sealed test (2026-01-02 → 2026-11-12)

**Order of events (provable from the git history):**
1. 2026 data deleted from the machine at the start of Step 0 (Step 0, commit `1278364`; the audit script asserts none is present).
2. Final skill code committed and pushed: commit `42db323` ("FREEZE POINT"). Latest data on disk then: 2025-12-31.
3. Only after that: `scripts/step5_fetch_sealed.py` downloaded 2026 into a separate folder (`data_sealed/`).
4. `final/run.py 2026-01-01 2026-11-12` run once — `final/` unchanged since the freeze commit (no diff).
5. `scripts/score_sealed.py` — the same scoring functions used for every repo.

Raw: `results/05_sealed_scores.csv`, predictions `results/preds/final_sealed_*.parquet`,
30 closing-price repairs applied by the Step 3.17 rule: `results/05_sealed_close_repairs_2026.csv`.

## Result
| Task | Skill | Days | Rank IC | t-stat | Hit rate | Top-quintile net/yr | Equal-weight/yr | Verdict |
|---|---|---|---|---|---|---|---|---|
| Swing (500 stocks, 5-day) | **Final skill** | 212 | **0.0057** | 0.20 | 50.3% | 11.3% | 15.5% | **no proven edge** |
| Swing | random scores | 212 | −0.0018 | −0.25 | 49.9% | 10.3% | 15.5% | no proven edge |
| Swing | 12-1 momentum | 212 | 0.0180 | 0.58 | 50.7% | 16.7% | 15.5% | no proven edge |
| Day (Dow 30, 10:00→15:55) | **Final skill** | 218 | **0.0116** | 0.66 | 50.5% | −7.8% | 4.1% | **no proven edge** |
| Day | random scores | 218 | −0.0015 | −0.12 | 50.0% | −24.4% | 4.1% | no proven edge |
| Day | follow the first 30 min | 218 | −0.0116 | −0.66 | 49.8% | −13.1% | 4.1% | no proven edge |

## Reading it honestly
- **The final skill did not pass.** By the rule fixed in Step 0 (t > 2 and beat equal-weight after costs) both
  parts are "no proven edge" on data nobody had seen.
- **The sign held again.** Swing ranking was positive in 11 of 11 years (2016–2026), day ranking in 11 of 11.
  Three of those years (2024, 2025, 2026) played no part in choosing the formulas. So the effect is probably
  real — and far too small: a 50.3–50.5% hit rate.
- **It would have lost money relative to just holding the stocks:** −4.2 points a year for swing, and the
  day version cannot cover a 0.1% round-trip cost.
- In 2026 plain 12-1 momentum ranked better than the final skill (IC 0.018 vs 0.006) — after ranking worse
  in 2025. Neither is significant. This is what "no stable edge" looks like.

## Final answer to the project's question
*Can these repositories — or a skill built from their best parts — predict what stocks will do?*
On liquid US stocks, from price and volume alone, over 5-day and intraday horizons: **no, not to a degree
that survives costs and an honest unseen-data test.** What the project did produce and prove:
1. A referee (reference backtester + checker) and exact adapters for 8 engines — you can now trust a backtest number.
2. A list of 30+ specific silent errors in popular tools (reports 03_01–03_17), each reproduced.
3. A no-peeking test harness that turned every "looks profitable" result into a clear yes/no — and said no,
   including to our own skill.

## What could change the answer (not done; each needs new inputs)
- **Information beyond price and volume:** earnings dates and surprises, analyst revisions, news. Alpaca's
  news feed and SEC filings are reachable from this environment.
- **Less-liquid stocks**, where simple effects are larger — and trading costs are too.
- **Forward testing the LLM agents** (TradingAgents, ai-hedge-fund v2) day by day on the Alpaca paper
  account, the only peek-free way to test them. Needs an LLM API key and calendar time.
- **A longer sealed period.** 212 days cannot confirm an effect this small either way.
