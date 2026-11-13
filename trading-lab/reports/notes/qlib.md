# Qlib (microsoft/qlib) - Alpha158 + LightGBM, swing prediction test

Code: `skills/qlib/run.py` (run with the qlib env python). Output: `results/preds/qlib_swing.parquet`, score: `results/score_qlib.csv`, truncation test: `results/qlib_truncation_test.json`.

## Method (what is Qlib's own)
- Data -> Qlib binary: `lab.data.load_daily(stocks_only=True)` (501 symbols, 2016-2025) written as per-symbol CSV (+ `factor=1.0`) and converted with Qlib's own `scripts/dump_bin.py dump_all` (from `git clone --depth 1 microsoft/qlib` to /tmp/qlib_src, the only network use). Work dir /tmp/qlib_work.
- Features: `qlib.contrib.data.handler.Alpha158` (158 features, `Alpha158DL`), unchanged.
- VWAP: our data has no VWAP. I supplied `$vwap = (high+low+close)/3` (typical price) as an extra field so all 158 features stay (incl. VWAP0). This is an approximation, not true VWAP.
- Label (fitting only): `Ref($open, -6)/Ref($open, -1) - 1` (passed through the handler's `label` kwarg). Handler learn-processors are Qlib defaults: `DropnaLabel`, `CSZScoreNorm(label)` (per-day cross-sectional, no fitted statistics).
- Model: `qlib.contrib.model.gbdt.LGBModel`, hyper-parameters from `examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml` (task.model.kwargs): loss mse, colsample_bytree 0.8879, learning_rate 0.2, subsample 0.8789, lambda_l1 205.6999, lambda_l2 580.9768, max_depth 8, num_leaves 210. num_threads 20 -> 4 (4-core box). Added seed=42. `early_stopping_rounds=50`, `num_boost_round=1000` are LGBModel defaults, as in the benchmark.
- Processors: the benchmark config uses Alpha158 defaults: infer_processors = [] (no feature normalisation at all) and the label processors above. So nothing is fitted on data (fit_start/fit_end are passed as 2016-01-01/2022-12-31 for safety but unused). Features are raw, causal rolling expressions.
- Segments: train 2016-01-01 -> 2022-12-21, valid 2023-01-01 -> 2023-12-20, predict 2024-01-01 -> 2025-12-31.
  Purge: the label at t uses prices to t+6 trading days, so segment ends were moved 6 trading days earlier than 2022-12-31 / 2023-12-31. Verified from the prepared data: train rows 829,775 (dates 2016-01-04..2022-12-21), valid rows 122,244 (2023-01-03..2023-12-20). No train/valid label uses a price dated after 2022-12-30 / 2023-12-29 respectively (so none after 2023-12-31, and train never touches the valid year).
- Early stopping on the valid segment: best iteration 9 (valid l2 0.99711; it got worse after, 0.9994 at iter 40). Weak signal / heavy regularisation: the model is nearly a constant plus a few splits.
- Predictions: `model.predict(dataset, "test")` for every stock-day with features, 251,415 rows, 501 symbols, 2024-01-02..2025-12-31, coverage 1.0 vs the scorer's targets. One training run, seed 42.

## Problems and fixes
1. First launch: SyntaxError (`class=` kwarg) - typo, fixed before anything ran.
2. Second launch trained (best iter 9) then crashed in `LGBModel.fit` at `R.log_metrics`: the installed MLflow refuses its default file store (`./mlruns`). No predictions were produced and no score was looked at. Fix: initialise Qlib with `exp_manager` uri `sqlite:////tmp/qlib_work/mlflow.db` (logging only). Re-ran with identical settings and seed; same best iteration (9). Because the first run never produced predictions or metrics, this is a bug re-run and not a re-run after seeing VAL numbers.
3. VWAP missing (above).
4. Nothing pip-installed (pyqlib, lightgbm, pyarrow, pandas were already present). Optional CatBoost/XGB/torch modules are absent; not needed.

## Truncation test (seeded random.seed(2025), pairs in 2025)
For each pair the whole Qlib dir was rebuilt from data with date <= that day (dump_bin again), the handler re-run with end_time = that day, and the same saved model applied.
| symbol | date | full score | truncated score | max feature abs diff (158 features) |
|---|---|---|---|---|
| USB | 2025-08-04 | 0.007403 | 0.007403 | 0.0 |
| MTCH | 2025-02-04 | -0.011555 | -0.011555 | 0.0 |
| XEL | 2025-09-05 | -0.008757 | -0.008757 | 0.0 |
All identical. Caveat: the model itself is the full trained model (as specified); only feature construction was re-checked.

## Final metrics (unedited output of `scripts/score_skill.py qlib`)
| split | days | coverage | rank_ic | ic_tstat | hit_rate | top_minus_bottom | top_q_net_ann | equal_weight_ann | excess_net_ann | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| DEV | 246 | 1.0 | -0.0055 | -0.46 | 0.4974 | 0.00084 | 0.1875 | 0.1764 | 0.0111 | no proven edge |
| VAL | 244 | 1.0 | 0.0136 | 0.96 | 0.5051 | 0.00440 | 0.3461 | 0.1874 | 0.1587 | no proven edge |

Reading: VAL IC 0.014 with t=0.96 is not significant; DEV IC is slightly negative. The positive excess_net_ann on VAL (+15.9%) comes with an insignificant IC, so it is likely a high-beta/size tilt in a rising 2025 market rather than stock-picking skill (not analysed here).

## Reviewer double-checks
- VWAP is a proxy (H+L+C)/3.
- Early stop at iteration 9 means the model is very shallow; the benchmark hyper-parameters were tuned for CSI300 with 1-day labels, not US stocks with a 5-day label.
- Rows where `t+6` is beyond data end have no label but still get predictions (labels never used for test).
- Universe has survivorship bias per PROTOCOL section 1.
