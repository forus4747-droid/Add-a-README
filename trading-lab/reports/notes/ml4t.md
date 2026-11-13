# ML4T price/volume factors + LightGBM (skill ml4t_*)
Repo: stefan-jansen/machine-learning-for-trading (3rd ed.). Code: skills/ml4t/run.py (one run). Raw outputs: results/score_ml4t_*.csv, results/ml4t_truncation_test.csv, results/ml4t_gbm_info.json.
Searched notebooks/.py for alpha/factor/momentum/reversal/volatility/101 alphas/WorldQuant: no Alpha101/WorldQuant formulas exist in the repo (only a literature citation in 08 README). So the factors are the chapter-8 feature definitions and the us_equities_panel case-study features. 'CS' = case_studies/us_equities_panel.

## Factor table (DEV = 2024, VAL = 2025; from scripts/score_skill.py)
| name | formula | source | direction | DEV | VAL |
|---|---|---|---|---|---|
| ml4t_mom_skip1_21d | P_{t-1}/P_{t-21}-1 | 08_financial_features/01_price_volume_features.py:228 (cell 'Skip-1 Momentum') | + (momentum; higher better) | IC -0.0015 (t -0.07), TMB +0.00139, excess +0.013 | IC -0.0154 (t -0.59), TMB -0.00023, excess -0.002 |
| ml4t_mom_12_1 | P_{t-21}/P_{t-252}-1 | case_studies/us_equities_panel/03_financial_features.py:341-370 (compute_momentum_returns, Jegadeesh-Titman) | + | IC +0.0449 (t +1.84), TMB +0.00325, excess +0.086 | IC +0.0104 (t +0.38), TMB -0.00323, excess -0.093 |
| ml4t_volscaled_mom21 | ret21/(std(ret1,21)*sqrt252), floor 1e-10 | 08/01_price_volume_features.py:1186-1196 | + (momentum) | IC +0.0056 (t +0.24), TMB +0.00201, excess -0.001 | IC -0.0160 (t -0.69), TMB -0.00239, excess -0.139 |
| ml4t_reversal_1d | -ret_1d | 08/01:453 (Short-Term Reversal) | + (stated: fallers rise) | IC +0.0147 (t +0.73), TMB +0.00128, excess +0.006 | IC +0.0013 (t +0.05), TMB +0.00230, excess +0.056 |
| ml4t_reversal_5d | ret_5d | CS 03_financial_features.py:587,620 (reversal_rank; contrarian_composite uses 1-rank) | - (lower ret_5d better) | IC +0.0151 (t +0.74), TMB -0.00033, excess -0.050 | IC +0.0119 (t +0.49), TMB +0.00459, excess +0.132 |
| ml4t_ma_dist_atr21 | (close-SMA21)/ATR21 | 08/01:286-310 | + (>0 bullish, table l.283) | IC -0.0049 (t -0.22), TMB +0.00098, excess -0.036 | IC -0.0162 (t -0.73), TMB -0.00248, excess -0.138 |
| ml4t_slope21 | polyfit slope(21)/mean*21 | 08/01:420-436 | + (steeper = stronger trend; up-slope bullish) | IC -0.0048 (t -0.21), TMB +0.00086, excess -0.004 | IC -0.0117 (t -0.47), TMB -0.00023, excess -0.044 |
| ml4t_vwap_dist5 | close/(sum(tp*V,5)/sum(V,5))-1, tp=(H+L+C)/3 | 08/01:1079-1118 | + (positive = buying pressure) | IC -0.0164 (t -0.84), TMB -0.00048, excess -0.062 | IC -0.0057 (t -0.23), TMB -0.00429, excess -0.089 |
| ml4t_vol_parkinson21 | sqrt(252*mean21((lnH-lnL)^2/(4ln2))) | 08/01:582-586 | raw: no direction stated | IC -0.0187 (t -0.58), TMB +0.00148, excess +0.000 | IC +0.0203 (t +0.54), TMB +0.00681, excess +0.182 |
| ml4t_vol_ratio_10_63 | std10(logret)/std63(logret) | 08/01:858-873 | raw: no direction stated | IC -0.0073 (t -0.60), TMB +0.00001, excess -0.049 | IC -0.0055 (t -0.45), TMB +0.00072, excess -0.049 |
| ml4t_rel_volume21 | V/SMA21(V) | 08/01:968-977 | raw: no direction stated | IC -0.0023 (t -0.24), TMB -0.00012, excess -0.026 | IC -0.0064 (t -0.58), TMB -0.00178, excess -0.072 |
| ml4t_amihud21 | mean21(|ret|/(close*V+1)) | CS 03:556-566 and text l.491-505 (illiquidity positively predicts returns) | + (stated) | IC -0.0301 (t -1.44), TMB -0.00120, excess -0.079 | IC -0.0092 (t -0.47), TMB +0.00253, excess +0.076 |
| ml4t_gbm | LightGBM on the 12 factors | 12_gradient_boosting/02_gbm_comparison.py:~1020 (regression, lr .05 leaves 31) and CS config/lgb/default_mse.yaml | n/a | IC +0.0124 (t +0.86), TMB +0.00249, excess +0.045 | IC +0.0023 (t +0.12), TMB +0.00450, excess +0.125 |

All verdicts: 'no proven edge'. Full metric columns are in results/score_ml4t_*.csv.

## Method notes / deviations (be aware)
- Data: lab.data.load_daily(stocks_only=True), already split+dividend adjusted; row-based windows (repo's session-counter gap handling not replicated; rows are consecutive sessions except rare gaps).
- ATR: repo uses ml4t.engineer.atr (library not installed, no internet use); I used TA-Lib Wilder ATR(21). Possible small difference from the repo library.
- Regression slope and Parkinson/ratios are my pandas/numpy ports of the repo's polars code.
- reversal_5d direction: repo never states a sign for ret_5d itself; sign taken from contrarian_composite = 1-rank(ret_5d) (CS l.620), i.e. lower 5d return = better. Fixed before looking at results.
- Volatility, vol-ratio, rel-volume: repo states no direction -> raw factor, as instructed.
- GBM: model = LightGBM regression, repo preset default_mse (objective regression, seed 42, max 500 rounds, LightGBM defaults lr 0.1/31 leaves). Early stopping (50 rounds) on 2023 L2 is the task's addition (repo has none). Label = open[t+1]->open[t+6] clipped +-50%. Train rows: date<=2022-12-31 AND label end<=2022-12-31 (702,384 rows); early-stop rows: 2023 dates with label end<=2023-12-31 (122,201). Features: per-day cross-sectional pct-rank minus 0.5 of the (signed) factors; rows with any NaN feature dropped. One run, seed 42, deterministic.
- PROBLEM: early stopping chose best_iteration = 1 (validation L2 never improved after the first tree), so the GBM is essentially a one-tree model with near-zero signal. Not re-run or tuned (rules: one run). VAL numbers are as produced.
- Row-shift targets (t+1, t+6 rows) as in lab.score.

## Truncation test
For each of 6 families (momentum, reversal, trend, volatility, volume, liquidity) 3 random (symbol,date) pairs in 2024-25 (rng seed 7) were recomputed on a copy of the whole universe cut at that date; factors matched the full run exactly (max abs diff 0). GBM: 3 more pairs, features recomputed on cut data, same-day rank, same trained model -> identical scores (diff 0). Result PASS (21/21). Details: results/ml4t_truncation_test.csv.
