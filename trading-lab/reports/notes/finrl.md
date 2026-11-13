# FinRL (AI4Finance) - Stock_NeurIPS2018 pipeline, PPO + A2C, Dow 30

Code: `skills/finrl/run.py` (train + trade + outputs), `skills/finrl/truncation_test.py`. Models: `skills/finrl/models/{ppo,a2c}.zip`.

## Method (FinRL pieces used)
- Features: `finrl.meta.preprocessor.preprocessors.FeatureEngineer`, `finrl.config.INDICATORS` = macd, boll_ub, boll_lb, rsi_30, cci_30, dx_30, close_30_sma, close_60_sma (via stockstats), `use_turbulence=True` (`calculate_turbulence`, from our price data), `use_vix=False` (VIX needs a download - skipped).
- Env: `StockTradingEnv` (`env_stocktrading.py`): hmax=100, initial 1,000,000, buy/sell cost 0.1% each side (tutorial default), reward_scaling 1e-4, state = cash + 29 prices + 29 holdings + 8*29 indicators. Trade env uses turbulence_threshold=70 (tutorial value; liquidates when turbulence >= 70; 62 such days in 2024-25).
- Agents: `DRLAgent` + SB3 PPO (`PPO_PARAMS` n_steps 2048, ent_coef .01, lr 2.5e-4, batch 64) and A2C (`A2C_PARAMS` n_steps 5, ent_coef .01, lr 7e-4), MlpPolicy.
- Train 2016-01-01..2023-12-31 only, total_timesteps = 50,000 each, seed 42, no tuning, single run.
- Trade 2024-01-01..2025-12-31 day by day, `model.predict(deterministic=True)`; score = raw action in [-1,1] (recorded before turbulence override / hmax scaling).
- Universe: 29 names. WBA dropped (history ends 2025-08-27, FinRL clean_data drops tickers with gaps anyway).

## Account curve (results/finrl_account_values.csv)
2024 from continuous run (account $1M on 2024-01-02); 2025 from a separate run restarted with $1M cash on 2025-01-02 (so 2025 actions in that run differ from the prediction-file run, whose state carries 2024 holdings). Equal-weight B&H: $1M split equally at first close of each period, held.
| Period | PPO | A2C | Equal-weight B&H |
|---|---|---|---|
| 2024 DEV | +0.19% | -0.11% | +14.18% |
| 2025 VAL | +5.39% | -0.12% | +16.56% |

## Scorer (score_skill.py, unedited)
| skill | split | rank_ic | t | hit | top-bottom | top_q_net_ann | EW ann | excess | verdict |
|---|---|---|---|---|---|---|---|---|---|
| ppo | DEV | -0.0113 | -0.40 | .5021 | -0.00344 | -0.0177 | 0.1413 | -0.1590 | no proven edge |
| ppo | VAL | 0.0315 | 1.28 | .5088 | 0.00331 | 0.1202 | 0.1811 | -0.0609 | no proven edge |
| a2c | DEV | -0.0601 | -2.08 | .4741 | -0.00377 | 0.0454 | 0.1413 | -0.0959 | no proven edge |
| a2c | VAL | -0.0419 | -1.36 | .4757 | -0.00455 | 0.0163 | 0.1811 | -0.1648 | no proven edge |
Note: "coverage 0.058" = only the 29 Dow names are in the preds vs ~500 in the scorer's target universe; each day has 29 >= 20 names, so it is scored on the Dow only.

## Truncation test (results/finrl_truncation.json)
Random dates 2025-02-28, 2025-05-02, 2025-12-19 (seed 7). For each, raw data cut at t, full FeatureEngineer + turbulence rerun, env replayed from 2024-01-01 to t with the saved model: max |action diff| = 0.0 for PPO and A2C on all 3; features (indicators, turbulence, close) for all rows <= t identical (max diff 0.0). Code review: stockstats indicators are causal rolling/ewm; turbulence uses rows < t plus current row; no scaler/VecNormalize anywhere; `df.ffill().bfill()` can only back-fill leading warm-up rows (none are NaN here). Only the final `data_split` upper bound is by date.

## Problems / fixes
- pyarrow missing in finrl env: installed `pyarrow==26.0.1` (uv pip).
- No pandas incompatibility surfaced (pandas 2.2.3, SB3 2.9.2, numpy 2.4.6); FinRL's own `DRL_prediction` discards per-day raw actions (it saves executed share counts), so a custom loop over the env was written.
- Running took ~8 min (session was interrupted once; outputs were complete on disk and the run was not repeated or altered).

## Caveats for reviewers
- FinRL fills trades at the same day-t close it observed (action on state of day t executes at close t), an optimistic convention vs the scorer's open[t+1] target; scorer is unaffected.
- A2C actions saturate at +-1 (mean -0.12, std 0.92); PPO small (std 0.19). Both 50k steps = ~25 passes over training data for PPO budget-wise; budget not raised after seeing results.
- Agents hold much cash (PPO/A2C ~flat vs buy-and-hold up 14-17%), so account comparison largely reflects low exposure.
