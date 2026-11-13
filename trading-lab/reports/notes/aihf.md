# virattt/ai-hedge-fund v1 technical signals (prediction test P, swing)

Source: `src/agents/technicals.py` at commit 6c41ae8cf5fb4e30eb8cdb6a816eb56ff234989d (last commit before v2 removed it). No LLM, no network.
Code: `skills/aihf/technicals_v1.py` (verbatim copy), `skills/aihf/run.py` (entry). Equivalence output: `results/aihf_equivalence.json`.

## Method
- Functions copied verbatim: calculate_trend/mean_reversion/momentum/volatility/stat_arb_signals, weighted_signal_combination,
  helpers calculate_rsi/bollinger_bands/ema/adx/atr/hurst_exponent, safe_float. Weights (trend .25, mean_reversion .20, momentum .25,
  volatility .15, stat_arb .15) copied from `technical_analyst_agent`.
- Unavoidable edits: imports reduced to math/pandas/numpy (graph/LLM/api/progress imports removed); `technical_analyst_agent` and
  `normalize_pandas` not copied. Maths untouched (a byte-compare of every copied function body vs source passed; safe_float differs only by surrounding whitespace in my check).
- Input: one stock's daily bars as a DataFrame indexed by DatetimeIndex "Date" (as the repo's `prices_to_df`), columns open/high/low/close/volume (from lab.data, split+dividend adjusted).
- Score = +confidence if bullish, -confidence if bearish, 0 neutral. aihf_combined = repo's weighted_signal_combination (its own weights); score = same conversion
  of its (signal, confidence). Names: aihf_trend, aihf_meanrev, aihf_momentum, aihf_volatility, aihf_statarb, aihf_combined.
- Option (a): vectorised per stock (full-history rolling/ewm, which are causal; threshold logic with np.where, NaN semantics identical to the Python `if`s;
  trend/bollinger/ema/adx reuse the repo helper functions on the full series), history from 2016 as lookback, output 2024-01-01..2025-12-31 (251,415 stock-days, 501 stocks).
- No fitting, repo defaults only.

## Equivalence / truncation test
300 random (symbol, date) pairs (seed 7, includes first and last output dates). For each, the verbatim functions were run on that stock's data cut at date
(all bars <= date, from 2016) and compared with the vectorised score: **max abs diff = 0.0 for all six names** (0 pairs differ by >1e-9).
Non-zero scores are common in the sample, so this is not trivially satisfied (share non-zero over all rows: trend .77, meanrev .13, momentum .26, vol .37, statarb .33, combined .54).

## Problems / findings
1. **Hurst exponent bug in the repo.** `calculate_hurst_exponent` does `np.subtract(price_series[lag:], price_series[:-lag])` on pandas Series; pandas aligns on the index,
   so every difference is p[i]-p[i]=0 on the overlap and NaN elsewhere. tau = max(1e-8, sqrt(0)) = 1e-8 for all lags, the log-log slope is ~4.7e-16 (float noise) for every stock-day
   (verified with both DatetimeIndex and RangeIndex, pandas 2.3.3). So H is always ~0 < 0.4, and stat_arb reduces to: skew(63d) > 1 -> bullish, < -1 -> bearish, confidence = (0.5-H)*2 = 1 - 1e-15.
   Kept verbatim (task: change nothing in maths). The vectorised code takes H from running the verbatim function once; each sampled pair re-checked it against the real function (diff 0).
   History length does not matter for H, so no expanding-statistics issue; no other expanding statistics exist in the file.
2. **aihf_statarb: scorer returns "no output".** The score takes only 3 distinct values per day (0, +0.999999999999999, -0.999999999999999), and `lab/score.py` skips days with
   `score.nunique() < 5`, so zero days qualify. I did not change the scorer, add tie-breaking noise, or alter the signal. Not a measured "no edge"; it is untestable with this scorer and the repo's behaviour.
3. `calculate_adx` mutates the input DataFrame (adds columns); I pass copies. Other functions are side-effect free.
4. Confidence for neutral is the constant 0.5 in the repo but neutral is scored 0 per the task, so neutral and "no signal" coincide.
5. Not run: no day task (swing only).

## Results (from scripts/score_skill.py, results/score_aihf_*.csv)
See final message / csv files. None passes the PREDICTS rule (ic_tstat > 2 and excess_net_ann > 0).
