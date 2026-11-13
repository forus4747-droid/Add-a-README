# Step 4 — The final skill

Code: `final/skill.py` (frozen), `final/features.py`, `final/day_features.py`, `final/run.py`.
Selection evidence: `results/04_walkforward*.csv`, `results/04_feature_stability.csv`, `results/04_day_walkforward.csv`.
Scores: `results/score_final.csv`, `results/04_final_by_year.csv`. No-look-ahead proof: `results/04_final_truncation.json`.

## How it was chosen (training data 2016–2023 only; nothing later was read during selection)
| Round | What was tried | Result inside training years | Decision |
|---|---|---|---|
| 1 | Machine-learning rankers on 43 features (ridge, 3 boosted-tree settings, blend), tested year by year 2019–2023 | mean rank IC 0.006–0.010; negative in 2022 | too weak and unstable |
| check | Each feature alone, per year | **Short-term reversal (1/2/5-day return) had the same sign in 8 of 8 years.** Size/liquidity features looked strongest (t ≈ 2.6) | size/liquidity **rejected**: the stock list was picked by 2022 trading volume, so earlier-small stocks on it are survivors that grew — hindsight, not prediction |
| 2 | Models on restricted feature sets vs two fixed reversal formulas | formulas: positive 8 of 8 years; models: 3 of 5 | simple formula beats the models |
| 3 | Four reversal formulas declared in advance; rule fixed beforehand: most positive years, ties by mean IC | V1 (1/2/5-day): 8 of 8, mean IC 0.0148 | **V1 selected** |
| day | Four intraday formulas, same rule, 2016 – mid-2024 | "fade the first 30 minutes": 9 of 9 periods, mean IC 0.031 | **selected** |

## The skill
- **Swing:** each day rank all stocks by their 1-, 2- and 5-day returns; score = minus the average rank.
  Stocks that fell most recently are expected to do better over the next 5 trading days.
- **Day:** at 10:00 rank the Dow stocks by their first-half-hour return; score = minus the rank.
  The weakest openers are expected to do better from 10:00 to 15:55.
- No fitted parameters. Truncation test: 5 random dates each, scores recomputed from data cut at that date
  are identical (difference 0.0).

## Results by year (2016–2023 were used to choose the formulas; 2024 and 2025 were not)
| Year | Role | Swing rank IC | Swing t | Swing top-quintile vs equal-weight, net | Day rank IC | Day t | Day spread per trade | Day net of 0.1% cost |
|---|---|---|---|---|---|---|---|---|
| 2016 | train | 0.003 | 0.13 | −1.4% | 0.079 | 5.37 | 0.088% | −12% |
| 2017 | train | 0.003 | 0.17 | −3.2% | 0.045 | 3.19 | 0.039% | −18% |
| 2018 | train | 0.006 | 0.30 | −2.4% | 0.011 | 0.70 | −0.002% | −24% |
| 2019 | train | 0.010 | 0.41 | −5.5% | 0.044 | 2.79 | 0.089% | −11% |
| 2020 | train | 0.044 | 1.26 | +28.0% | 0.013 | 0.77 | 0.131% | −17% |
| 2021 | train | 0.012 | 0.40 | +1.2% | 0.027 | 1.75 | 0.016% | −24% |
| 2022 | train | 0.025 | 0.88 | +5.7% | 0.026 | 1.54 | 0.026% | −27% |
| 2023 | train | 0.016 | 0.68 | +4.5% | 0.012 | 0.87 | 0.007% | −25% |
| **2024** | **unseen** | **0.018** | 0.92 | −3.7% | **0.010** | 0.74 | −0.006% | −26% |
| **2025** | **unseen** | **0.006** | 0.25 | +7.9% | **0.025** | 1.64 | −0.005% | −23% |

## Verdict by the protocol's own rule (rank IC t-stat > 2 **and** beats equal-weight after costs, on VAL 2025)
| Skill | VAL 2025 | Verdict |
|---|---|---|
| Swing | IC 0.006, t 0.25, +7.9% excess | **no proven edge** |
| Day | IC 0.025, t 1.64, −23% after costs | **no proven edge** |

## What is and is not established
- **Established:** the direction of both rankings was right in 10 of 10 years, including the two years not
  used for selection. That is more consistent than anything tested in Step 3 (those flipped sign between
  2024 and 2025). The effect is real in sign.
- **Not established:** that it is large enough to matter. Swing hit rate is ~50.5%; in no single year does
  it clear the t > 2 bar, and its profit versus simply holding all stocks was negative in 5 of 10 years.
- **The day skill cannot pay its costs.** Its edge per trade was ~0.09% in 2016–2019, and has been about
  zero since 2023 — against a 0.10% round-trip cost. The pattern has been competed away.
- **Is it "much better than all the repositories"? No.** It is more consistent and it is honest about its
  size, but it is not a money-making predictor, and this report does not claim it is.

## What the final repository keeps, fixes and drops
| Kept (verified) | From | Fixed | Dropped |
|---|---|---|---|
| Data loader + integrity audit + sha256 manifest | this project | Alpaca daily closes: 418 stray prints repaired (03_17) | pandas-ta own indicators (4 wrong) |
| Reference backtester with hand-checked tests | this project | ai-hedge-fund Hurst: not reused (always ~0) | OpenBB price wrapper (dividend trap) |
| vectorbt adapter (primary engine) | vectorbt | backtesting.py: 3 documented workarounds in its adapter | Freqtrade, Jesse, vn.py, Zipline as stock engines |
| NautilusTrader adapter (realism check) | nautilus_trader | NautilusTrader: precision + next-open configuration | FinRL agents |
| Feature library (43 price/volume features) | ML4T, Qlib Alpha158, ai-hedge-fund, Freqtrade | size/liquidity features flagged as universe-biased | Qlib/ML4T default models, RSI sample strategies |
| Scoring harness + no-peeking protocol + truncation tests | this project | S1 rule wording clarified | — |
| Final skill (two formulas) | selected in this step | — | — |

Next: Step 5 downloads 2026 for the first time and runs `final/run.py` once.
