# Test Protocol v2 (frozen before any test was run)

v1 (commit 1) compared engines only. v2 (this file) refocuses on the stated goal: **can each repo's
"skill" predict what stocks did, on data it has not seen?** Committed before Step 2. Later changes need a
new commit that says why.

## 1. Data
| Set | Content | Source |
|---|---|---|
| `5min/` | 30 Dow stocks, 5-min bars, regular hours, split-adjusted, 2023-08-01 → 2025-12-31 | Alpaca SIP, `scripts/fetch_data.py`; same as Drive folder "Day Trader Backtest Data" |
| `daily/daily.parquet` | ~550 symbols, daily bars, split+dividend adjusted, 2016-01-01 → 2025-12-31 | Alpaca SIP, `scripts/fetch_daily.py` |

- Daily universe = top 500 common stocks by median dollar volume in **2022-H2** (chosen using only data from
  before every test period) + 20 ETFs + the 30 Dow stocks.
- **Known limitation:** candidates come from today's listing files, so stocks delisted between 2023 and
  today are missing (except WBA). This flatters all strategies slightly and equally; it does not favour one repo.
- Data files are not committed (too large). `reports/01_data_manifest.csv` records a sha256 per file.

## 2. Time splits — the "no peeking" rule
| Split | Dates | Used for |
|---|---|---|
| TRAIN | 2016-01-01 → 2023-12-31 (daily); 2023-08-01 → 2024-06-30 (5-min) | fitting models |
| DEV | 2024-01-01 → 2024-12-31 (daily); 2024-07-01 → 2024-12-31 (5-min) | tuning, debugging, fixing |
| VAL | 2025-01-01 → 2025-12-31 | scoring every repo; nothing is fitted or tuned on it |
| SEALED | 2026-01-01 → 2026-11-12 | final skill only, one run, Step 5 |

- **SEALED data is not on this machine.** The 2026 files were deleted on 2026-11-13 and are downloaded
  again only in Step 5, after the final skill's code is committed. Peeking is impossible, not just forbidden.
- A prediction for day t may use only bars that closed on or before day t. Trades fill at the next bar's open.
- LLM-based repos are excluded: language models have 2023–2026 market history in their training data,
  so a backtest over those years cannot be made peek-free.

## 3. What is tested
**P. Prediction test (the main test).** Each skill outputs, for every symbol and day, a score = "how much I
expect this to go up". Scores are compared with what really happened next.
- Swing target: return from next day's open to the open 5 trading days later (daily universe).
- Day target: return from the 10:00 bar's open to the 15:55 bar's open, predicted from bars before 10:00 (Dow 30).
- Metrics on VAL: (1) rank IC = Spearman correlation between score and realised return, averaged per day,
  with t-statistic; (2) hit rate = % of times the sign of the score matched the sign of the return
  (relative to the day's cross-section median); (3) top-minus-bottom quintile return per period;
  (4) long top-quintile portfolio, net of 0.05% cost per side, vs equal-weight universe and vs SPY.
- Baselines every skill must beat: random scores (IC ≈ 0), equal-weight buy-and-hold, 12-1 momentum, 5-day reversal.
- A skill "predicts" only if its VAL rank IC is positive with t-stat > 2 AND its top quintile beats
  equal-weight after costs. Otherwise it is recorded as "no proven edge".

**E. Engine accuracy test.** A backtest engine that miscalculates makes every later conclusion wrong, so each
engine runs two fixed rule strategies (S1 opening-range breakout on 5-min, S2 20/50 SMA cross on daily; exact
rules in `protocol/STRATEGIES.md`) and its trade list is compared with an independent plain-Python reference.
Pass = same trades, same timestamps, net P&L within $0.01 per trade.

**D. Data/indicator accuracy test.** Indicator libraries vs hand-computed formulas (tolerance 1e-6);
alternative data sources vs our Alpaca data (daily close within 0.5%).

## 4. Repo → test mapping
| Repo | Test | Skill tested |
|---|---|---|
| microsoft/qlib | P | Alpha158 features + LightGBM (its standard pipeline) |
| AI4Finance/FinRL | P | PPO/A2C agent on Dow 30 with its standard indicators |
| virattt/ai-hedge-fund | P | its rule-based technical signals (trend, mean-reversion, momentum, volatility) — no LLM |
| stefan-jansen/machine-learning-for-trading | P | its documented alpha factors |
| freqtrade | P + E | its bundled sample strategy signals; engine |
| backtesting.py, backtrader, vectorbt, nautilus_trader, zipline-reloaded, jesse, vnpy | E | engine |
| TA-Lib, pandas-ta | D | indicators |
| yfinance, OpenBB | D | data vs Alpaca |
| QuantConnect/Lean | not testable | needs Docker + blocked host |
| TradingAgents | excluded | LLM (see §2) |
| ccxt, hummingbot, OctoBot, ib_async | not testable | need crypto exchanges / broker gateway, blocked here |
| alpaca-py | used | it is the data source itself |

## 5. Process rules
- One repo at a time, order in `reports/00_INDEX.md`. For each: adapter → run → compare → record every
  problem → find cause → fix or mark as a real limitation → commit report + raw results.
- A repo's result is never edited after seeing another repo's result.
- Fixes to a skill are developed on TRAIN/DEV only and re-scored on VAL once; both before and after
  numbers are kept.
- Every number in a report comes from a file in `results/` produced by a script in this repo.
