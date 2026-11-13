# Indicator accuracy: TA-Lib vs pandas-ta vs independent reference

Script: `scripts/test_indicators.py` (run from the lab folder with the core env python). Outputs in `results/`:
`indicators_summary.csv` (indicator x library x symbol), `indicators_summary_by_indicator_library.csv`, `indicators_cause_proofs.csv`,
`indicators_talib_vs_pandasta.csv`, `indicators_vwap.csv`, `indicators_edge_cases.csv`, `indicators_extra_checks.csv`,
`indicators_defaults.csv`, `indicators_detail_raw.csv`, `indicators_versions.json`.

Versions: TA-Lib python wrapper 0.8.3 (C library 0.8.3, built Oct 28 2026), pandas-ta 0.4.71b0, numpy 2.2.6, pandas 2.3.3.
Data: daily AAPL, KO, AMC, INTC, SPY (2514 bars each, 2016-01-04..2025-12-31, no NaN, sorted); MSFT 5-min (47,368 bars) for VWAP.
Libraries tested in three modes: `talib` (direct), `pandas_ta[talib=True]` (default; delegates to TA-Lib where it can), `pandas_ta[talib=False]` (pandas-ta's own code).

## Method and tolerances
References are plain numpy loops (no talib/pandas_ta import is used by any reference function). Comparison: all bars where both are valid
(max abs, max rel = |d|/max(|ref|, 1e-8*scale)), the last 1000 bars only, first valid index of each, NaN-pattern mismatches, and the last bar
index at which |diff| exceeded tolerance (shows how fast a start-up difference decays).
Match = max abs diff over last 1000 bars <= tol and no NaN where the reference is valid in that window. tol: 1e-6 x mean close of the symbol for
price-unit indicators (SMA, EMA, WMA, MACD, BB, ATR); 1e-8 x max|OBV| for OBV; 1e-6 absolute for the dimensionless 0-100/percent indicators
(RSI, ADX, STOCH, CCI, ROC, WILLR, MFI). "startup_only_diff" = passes the last-1000 test but differs by more than tol earlier.

## Reference formulas
| Indicator | Formula | Source |
|---|---|---|
| SMA(20) | mean of last 20 closes | StockCharts ChartSchool "Moving Averages" |
| EMA(20) | alpha=2/(n+1); seed = SMA of first n closes at bar n-1; EMA_t = a*C_t + (1-a)*EMA_{t-1} | StockCharts "Moving Averages" |
| WMA(20) | sum(i*C_i, i=1..n, newest weight n) / (n(n+1)/2) | StockCharts / Investopedia WMA |
| RSI(14) | changes; first avg gain/loss = simple mean of first 14; then avg=(prev*13+cur)/14; RSI=100-100/(1+RS); loss=0 -> 100 | Wilder 1978 ch. 6; StockCharts RSI |
| MACD(12,26,9) | EMA12 (seed bar 11), EMA26 (seed bar 25); line=diff from bar 25; signal=EMA9 of line seeded by SMA of first 9 line values (bar 33); hist=line-signal | Appel; StockCharts MACD |
| Bollinger(20,2) | mid=SMA20; bands = mid +/- 2*population SD (ddof=0) | Bollinger; StockCharts Bollinger Bands |
| ATR(14) | TR=max(H-L,|H-Cprev|,|L-Cprev|); first ATR = mean of first 14 TR; ATR=(prev*13+TR)/14. Both TR0=H-L (StockCharts) and TR from bar 1 (Wilder's original) are implemented | Wilder 1978 ch. 3; StockCharts ATR |
| ADX(14) | +DM/-DM/TR from bar 1; Wilder-smoothed sums (seed sum of first 14, then S-S/14+x); DI=100*S_DM/S_TR; DX=100|+DI - -DI|/(+DI + -DI); first ADX = mean of first 14 DX; then (prev*13+DX)/14 (first value bar 27) | Wilder 1978 ch. 5; StockCharts ADX |
| Stochastic(14,3,3) | raw %K=100(C-LL14)/(HH14-LL14); slow %K=SMA3(raw); %D=SMA3(slow %K) | Lane; StockCharts Stochastic Oscillator |
| CCI(20) | TP=(H+L+C)/3; (TP-SMA20(TP))/(0.015*mean absolute deviation about the window mean) | Lambert; StockCharts CCI |
| OBV | cumulative +/-volume on close up/down; OBV_0 = volume_0 (constant start is arbitrary) | Granville; StockCharts OBV |
| ROC(10) | 100*(C_t/C_{t-10}-1) | StockCharts ROC |
| Williams %R(14) | -100*(HH14-C)/(HH14-LL14) | StockCharts Williams %R |
| MFI(14) | TP*volume; positive/negative flow by TP vs previous TP (equal TP = no flow); MFI=100-100/(1+sumPos14/sumNeg14) | Quong & Soudack; StockCharts MFI |
| VWAP | cumulative sum(TP*vol)/cumulative sum(vol), reset each New York session date, TP=(H+L+C)/3 | StockCharts VWAP |

## Results, aggregated per indicator x library (worst of the 5 symbols)
fv = first valid index (ref in brackets if different). "last-1000" = max abs diff over the last 1000 bars. exc = last bar at which the diff exceeded tol (-1 = never).

| Indicator | Library | fv | max abs diff (all) | max abs diff (last 1000) | match | note |
|---|---|---|---|---|---|---|
| SMA | talib / pta[T] / pta[F] | 19 | 1.4e-12 / 1.4e-12 / 2.3e-13 | same | yes | |
| EMA | talib / pta[T] / pta[F] | 19 | 4.5e-13 / 4.5e-13 / 0 | same | yes | |
| WMA | talib / pta[T] / pta[F] | 19 | 4.1e-12 / 4.1e-12 / 2.3e-13 | same | yes | |
| RSI | talib, pta[T] | 14 | 5.0e-14 | 5.0e-14 | yes | |
| RSI | pta[F] | 1 (14) | 30.9 | 4.3e-14 | yes (start-up only) | exc bar 254; emits values from bar 1 |
| MACD line | talib, pta[T] | 33 (25) | 0.0716 | 3.4e-13 | yes (start-up only) | exc bar 73 |
| MACD signal | talib, pta[T] | 33 | 0.153 | 3.3e-13 | yes (start-up only) | exc bar 81 |
| MACD hist | talib, pta[T] | 33 | 0.0814 | 2.4e-13 | yes (start-up only) | exc bar 79 |
| MACD line/signal/hist | pta[F] | 25 / 33 / 33 | 0 | 0 | yes | exactly textbook |
| BB upper/mid/lower | talib, pta[T] | 19 | 1.0e-11 | 8.1e-12 | yes | |
| BB mid | pta[F] | 19 | 2.3e-13 | 2.3e-13 | yes | |
| BB upper/lower | pta[F] | 19 | 3.24 | 1.22 | NO | persistent, never converges |
| ATR | talib, pta[T] | 14 | 1.1e-14 | 1.1e-14 | yes | |
| ATR | pta[F] | 13 (14) | 0.121 | 1.1e-14 | yes (start-up only) | exc bar 109 |
| ADX | talib, pta[T] | 27 | 1.80 | 4.3e-14 | yes (start-up only) | exc bar 261 |
| ADX | pta[F] | 14 (27) | 20.6 | 5.0e-14 | yes (start-up only) | exc bar 285; emits 13 bars before warm-up |
| Stoch %K | talib, pta[T] | 17 (15) | 7.1e-13 | 7.1e-13 | yes | output starts 2 bars later than textbook |
| Stoch %K | pta[F] | 15 | 3.8e-13 | 3.8e-13 | yes | |
| Stoch %D | all three | 17 | 6.5e-13 | 6.5e-13 | yes | |
| CCI(20) | talib, pta[T] | 19 | 1.7e-11 | 7.4e-12 | yes | |
| CCI(20) | pta[F] | 19 | 36,801 | 23,191 | NO | garbage values (bug) |
| OBV | talib, pta[T] | 0 | 0 | 0 | yes | |
| OBV | pta[F] | 1 (0) | 2.88e8 | 2.88e8 | NO | constant offset = volume[0], bar 0 NaN |
| ROC | all three | 10 | 5.7e-14 | 2.8e-14 | yes | |
| Williams %R | all three | 13 | 2.8e-14 | 2.8e-14 | yes | |
| MFI | talib, pta[T] | 14 | 2.7e-12 | 2.7e-12 | yes | |
| MFI | pta[F] | 14 | 7.90 | 5.70 | NO | intermittent, up to ~8 points |
| VWAP | pandas_ta (anchor D) | 0 | 4.5e-13 | 2.8e-13 | yes | same with naive NY, UTC-aware and NY-aware index |

Per-symbol rows (including AMC with its reverse-split price jumps) are in `indicators_summary.csv`; the pattern is identical for all five symbols.

## Direct talib vs pandas-ta comparison (`indicators_talib_vs_pandasta.csv`)
- `pandas_ta[talib=True]` equals `talib` exactly (diff 0.0) for every indicator at the tested parameters. It is a thin wrapper.
- `pandas_ta[talib=False]` differs from `talib` (last-1000 diffs): BB upper/lower 1.22, CCI 23,191, OBV 2.9e8, MFI 5.70; start-up-only differences for RSI, ATR, ADX, MACD (pta[F] equals the textbook, talib seeds differently).
- The two modes of the SAME pandas-ta function therefore give different numbers for BBANDS, CCI, OBV, MFI by default; `talib=True` is the default only if TA-Lib is importable.

## Problems found, ordered by how much they could mislead a trader
1. **pandas-ta CCI (talib=False) is wrong** (`pandas_ta/momentum/cci.py`, non-talib branch): `typical_price - mean_typical_price / (c * mad)` is missing parentheses; should be `(tp - sma)/(c*mad)`. Values reach tens of thousands, and are +/-inf on flat series. Reproduced to 1.1e-11 by a reference with the same precedence (`CCI_ptabug`). Only affects installs without TA-Lib or `talib=False`; and silently so.
2. **pandas-ta Bollinger Bands (talib=False) bands are 2.6% too wide** for n=20 (`pandas_ta/volatility/bbands.py`: ddof default 1 -> `statistics/stdev.py`; TA-Lib BBANDS and Bollinger/StockCharts use population SD ddof=0). Max band error 3.24 on price scale, never converges; the same function returns different bands depending on whether TA-Lib is installed. Reproduced by reference with ddof=1 (diff 1.4e-9 - the residue is pandas-ta's variance numerics). Workaround: pass `ddof=0, talib=False`, verified exact. With `talib=True` the ddof argument is silently ignored (verified).
3. **pandas-ta stoch(talib=True) ignores smooth_k** (`pandas_ta/momentum/stoch.py`): calls `STOCH(high, low, close, k, d, ma, d, ma)`, so the slow-%K period is `d`, not `smooth_k`. With k=14,d=3,smooth_k=5 the result differs from the correct value by up to 37 (%K) and 27 (%D) points, persistently (checked in `indicators_extra_checks.csv`; `talib=False` and raw `talib.STOCH(14,5,3)` are correct). Invisible at the default 14,3,3 (so it passes the requested test).
4. **NaN input silently poisons TA-Lib results** (edge-case test, NaN at bar 150 of 300): RSI and ADX do not return NaN; they return a frozen constant for the rest of the series (RSI stuck at 50.0, ADX stuck at its last value), up to 22.7 / 18.4 points away from the same indicator run on a forward-filled series. SMA, EMA, MACD, BBANDS, ATR, STOCH, MFI return NaN for the entire remainder of the series (permanent, even for non-recursive SMA/BB/STOCH/MFI; pandas-ta[F] STOCH too), whereas WMA, CCI, WILLR, ROC recover after one window. pandas-ta delegates, so it inherits all of this with `talib=True`; with `talib=False` EMA/MACD/ATR/RSI skip the NaN and carry on (ADX still freezes because its ATR comes from TA-Lib). Clean/fill data before indicators.
5. **pandas-ta OBV (talib=False) is offset by volume[0] and has NaN at bar 0** (`pandas_ta/utils/_core.py:signed_series` overwrites its own `initial` argument with `None`). Level of OBV is wrong by a constant (2.9e8 for AAPL); slope/divergence analysis is unaffected, but absolute levels and comparisons across libraries are. Reproduced exactly (`OBV_nan0`).
6. **pandas-ta MFI (talib=False) mishandles equal typical prices** (`pandas_ta/volume/mfi.py`): `where(tp > roll(tp), 1, -1)` is a strict float compare, so true ties (and float noise of ~1e-14 on ties) are counted as negative flow, for the next 14 bars. Diffs up to 7.9 MFI points on windows after each tie. TA-Lib treats |dTP|<1e-8 as no flow and matches the textbook (my reference, eps 1e-9, reproduces TA-Lib to 2.7e-12; strict compare + ties negative reproduces pandas-ta to 2.8e-14).
7. **pandas-ta RSI and ADX (talib=False) emit values before the warm-up and are not Wilder-seeded** (`momentum/rsi.py` uses `overlap/rma.py` = `ewm(alpha=1/n, adjust=False)` seeded by the first change; `trend/adx.py` non-talib branch seeds the same way, and its ATR still comes from TA-Lib because `talib=False` is not passed to `atr()`). RSI has values from bar 1 (textbook: 14) with errors up to 31 points; ADX from bar 14 (textbook 27) with errors up to 20.6. Decays: RSI within 1e-6 after bar 254, ADX after bar 285. Danger for short histories / freshly started live feeds only.
8. **pandas-ta ADX DMP/DMN columns change meaning with the mode**: with TA-Lib they are `PLUS_DM`/`MINUS_DM` (smoothed raw directional movement, price units), without it they are +DI/-DI (percent). Verified against my +DI/-DI: talib=False converges to 4e-14, talib=True is off by 62 (DMP) / 52 (DMN) in the last 1000 bars. The ADX line is correct in both.
9. **TA-Lib MACD and ADX start-up seeding differs from the textbook** (decaying). MACD: the fast EMA is seeded at bar slow-1 from the 12 bars ending there (not bars 0..11); line, signal and histogram are all NaN until bar 33 (textbook line from bar 25). Max difference 0.07-0.15 (about 0.05-0.1% of price scale), gone by bar ~80. ADX: Wilder sums are seeded from n-1 raw values with the n-th entering through the recursion; max difference 1.8, gone by bar ~261. Proven exact by `MACD_talib_seed` (3.4e-13) and `ADX_talib_seed` (5e-14). pandas-ta[F] MACD equals the textbook exactly (diff 0).
10. **pandas-ta ATR (talib=False)** seeds with TR0 = H-L (StockCharts) rather than Wilder/TA-Lib TR from bar 1; difference 0.12 max, decays by bar ~109 (`ATR_tr0`, 1.4e-14). Either seed is defensible.
11. **Defaults differ between libraries** (`indicators_defaults.csv`): pandas-ta SMA/EMA/WMA default length 10 (TA-Lib 30), BBANDS length 5 (TA-Lib's abstract-API table lists timeperiod 20; the direct wrapper default was not checked), CCI 14, STOCH k=14 (TA-Lib fastk 5). Always pass parameters explicitly; this test did.
12. Minor: TA-Lib Stoch %K and MACD line first output is 2 and 8 bars later than the textbook (aligned to %D / signal). pandas-ta returns `None` (not NaNs) when a series is shorter than its minimum, TA-Lib returns all-NaN.

Nothing was found wrong with SMA, EMA, WMA, ROC, Williams %R, VWAP in any mode, nor with RSI, ATR, ADX (steady state), BBANDS, CCI, OBV, MFI, STOCH in TA-Lib / pandas-ta[talib=True] at the tested parameters.

## Proof table (reference adjusted to the library's convention -> reproduces its output)
Source: `results/indicators_cause_proofs.csv`; the diff shown is the max abs over all bars and all 5 symbols, versus tolerance.
| Library behaviour | Adjusted reference | Max abs diff after adjustment |
|---|---|---|
| TA-Lib MACD seeding | `MACD_talib_seed` | 3.4e-13 (line), 3.3e-13, 2.4e-13 (tol 3.5e-4) |
| TA-Lib ADX seeding | `ADX_talib_seed` | 5.0e-14 (tol 1e-6) |
| pandas-ta ADX non-talib | `ADX_pta_py` | 2.1e-14 |
| pandas-ta RSI non-talib | `RSI_ewm_firstchange` | 5.0e-14 |
| pandas-ta ATR non-talib | `ATR_tr0` | 1.4e-14 |
| pandas-ta BB non-talib | `BB_ddof1` | 1.4e-9 (price units, tol 3.5e-4) |
| pandas-ta CCI non-talib | `CCI_ptabug` | 1.1e-11 |
| pandas-ta OBV non-talib | `OBV_nan0` | 0 |
| pandas-ta MFI non-talib | `MFI_tieneg` | 2.8e-14 |
Textbook convention: Wilder seeding of RSI/ATR/ADX (SMA of first n; ADX per Wilder 1978), EMA seeded with SMA (pandas-ta pure MACD does this; TA-Lib's fast-EMA seed is a TA-Lib choice), population SD for Bollinger, equal TP = no flow for MFI, CCI with parentheses as in Lambert, OBV start arbitrary (TA-Lib's volume[0] is the common choice).

## Edge cases (synthetic; `indicators_edge_cases.csv`)
- Constant price (300 bars of 100, volume 1000). TA-Lib and pandas-ta[T]: RSI 50.0 (not NaN, not 0/100), ADX 0, STOCH 0, WILLR 0, CCI 0, MFI 0, ATR 0, BB bands collapse to 100, ROC 0, OBV 1000 flat. pandas-ta[F]: RSI all NaN, ADX all NaN, WILLR all NaN, CCI -inf (281 +/-inf values), STOCH 0 (epsilon in `non_zero_range`), MFI 0, ATR 2.2e-16.
  The textbook value is undefined (0/0); a trader sees 50 or 0 from TA-Lib and a different number from pandas-ta[F] for the same flat market.
- NaN in the middle: see problem 4. Per indicator: talib/pta[T] permanent NaN: SMA, EMA, MACD x3, BB x3, ATR, STOCH x2, MFI; frozen finite: RSI, ADX; recover after window: WMA, CCI, WILLR, ROC, OBV (with a level shift of up to 4265). pta[F]: SMA/BB/CCI/WMA/WILLR/MFI recover after one window, EMA/MACD/ATR/RSI recover immediately, STOCH %K/%D stay NaN for the rest of the series (like TA-Lib), ADX frozen.
- Shorter than window (5, 19, 20 bars): TA-Lib returns all-NaN arrays without error. pandas-ta returns `None` for SMA, EMA, WMA, RSI, MACD, BB, ATR, CCI, STOCH, ROC, WILLR, MFI when below its minimum length (callers that index the result get `TypeError`); at 19 bars ADX/ATR/RSI/MFI/OBV/ROC/WILLR still return arrays. At exactly 20 bars everything but MACD returns an array. pandas-ta[F] ADX returns 5-6 early values at 19-20 bars where TA-Lib returns none.

## What a reviewer should double-check
- TA-Lib's C source (`ta_MACD.c`, `ta_ADX.c`, `ta_MFI.c`) is not on this machine. The TA-Lib conventions above were derived by exact numerical reproduction (1e-13), not by reading C code; the stated TA_IS_ZERO threshold for MFI is from my recollection of TA-Lib headers and only confirmed to the extent that eps in [1e-12, 1e-9] reproduces output. pandas-ta behaviours were confirmed in its source (paths are under `.../site-packages/pandas_ta/`).
- Tolerances for the dimensionless indicators are absolute 1e-6 (i.e. 1e-8 relative on a 0-100 scale), a choice of mine; "price scale" for price-unit indicators is the symbol's mean close.
- The reference's ATR defaults to Wilder's TR-from-bar-1 seed (matches TA-Lib); with the StockCharts TR0 seed ATR pta[F] would be the match. The "textbook" label for ATR seeding is therefore a convention, not a defect.
- The MFI tie threshold and RSI-on-constant (50.0) rest on installed TA-Lib 0.8.3 behaviour, which may differ in older TA-Lib releases.
- The NaN-gap test used one random-walk series with one NaN bar (all of OHLCV); the "ffilled run" yardstick is my choice of sane behaviour.
- pandas-ta 0.4.71b0 is a beta; the bugs listed may be fixed or differ in other releases. Only the five symbols and one intraday symbol were run.
- STOCH %K with talib output alignment (fv 17 vs 15) is a warm-up convention, not an error; comparison covers bars where both are valid.
