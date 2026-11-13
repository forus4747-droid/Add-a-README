# Step 3 summary — every repo, one line each

All results independently re-run or re-scored by the reviewer. Details in the linked reports.

## A. Backtest engines — can they calculate correctly? (9,304 day trades + 179 swing trades vs reference)
| Repo | Matches reference | Workarounds needed | Worst silent error if used as documented | Keep? | Report |
|---|---|---|---|---|---|
| vectorbt | yes | 1 (end-of-test close) | none found | **yes — primary engine** | 03_01 |
| Backtrader | yes | 2 | 21 final trades silently dropped; entries a day late | cross-check only | 03_04 |
| NautilusTrader | yes | 3 | fills at same bar's close; 2,803 prices rounded | **yes — realism check** | 03_03 |
| backtesting.py | yes | 3 | fee shrinks position; final P&L +2.4% wrong | only behind a wrapper | 03_02 |
| vn.py | yes | 5 | no market orders; no per-trade fees | no | 03_05 |
| Jesse | yes | 3 (heavy) | fills at current close; needs 1-min data | no | 03_06 |
| Freqtrade | yes | 3 | trades on Sundays: 284 trades vs 179, −$17,545 | no (for stocks) | 03_07 |
| Zipline | yes | 6 (heavy) | fills at close; prices rounded; bars dropped | no | 03_09 |
| LEAN | not testable | — | — | — | 03_16 |

## B. Predictors — did they predict 2025? (rank IC t-stat must exceed 2 AND beat equal-weight after costs)
| Repo / skill | Best VAL rank-IC t-stat | Verdict | Report |
|---|---|---|---|
| Qlib Alpha158 + LightGBM | 0.96 | no proven edge | 03_10 |
| FinRL PPO / A2C | 1.28 / −1.36; trailed buy-and-hold by 11–17 pts | no proven edge | 03_11 |
| ai-hedge-fund technical signals (5 + combined) | 0.36 | no proven edge; Hurst bug | 03_08 |
| ML4T 12 factors + boosted model | 0.54 | no proven edge | 03_12 |
| Freqtrade sample / minimal strategy signals | 0.61 | no proven edge | 03_13 |
| Baselines: momentum, reversal, random | 0.49 | no proven edge | 02 |
| TradingAgents, ai-hedge-fund v2 | excluded (LLM cannot be back-tested without peeking) | — | 03_16 |

## C. Data and indicators — are the numbers right?
| Repo | Verdict | Report |
|---|---|---|
| TA-Lib | accurate; one missing value silently corrupts the rest of a series | 03_14 |
| pandas-ta | own code wrong on CCI, Bollinger, OBV, MFI; ignores a Stochastic setting | 03_14 |
| yfinance | accurate (99.9% of days within 0.5%); silently drops delisted stocks | 03_15 |
| OpenBB | default prices ignore dividends; nothing usable without extra installs | 03_15 |
| alpaca-py data | 418 stray closing prices found and repaired; opens correct | 03_15, 03_17 |
| ccxt, Hummingbot, OctoBot, ib_async | not testable here | 03_16 |

## What Step 3 established
1. **Calculation is solvable, prediction is not solved.** Eight engines can be made exact. Zero public
   prediction recipes showed an edge on unseen 2025 data.
2. **Defaults are where the errors are.** Six of eight engines give different answers when used as their
   documentation suggests, and none warns.
3. **Apparent profit without ranking skill is market exposure.** Several skills showed +12% to +18% "excess"
   in 2025 with t-stats under 1 — they simply held volatile stocks in a rising year.
4. **Short windows lie.** Random scores reached t = 2.36 on a six-month window (Step 2).
5. **Every data source had at least one silent flaw**, including the one we trusted.

## Consequence for Step 4
There is no winning predictor to keep. The final repo therefore keeps the verified infrastructure
(data + repair, TA-Lib indicators with guards, vectorbt engine with the reference as referee, the scoring
harness, the no-peeking protocol) and builds one new skill designed around findings 3 and 4. It will be
judged by the same rule, on 2026 data that does not exist on this machine yet.
