# Step 3.14 — TA-Lib 0.8.3 and pandas-ta 0.4.71b0 (indicator accuracy test)

Worker notes with formulas, sources and proofs: `reports/notes/indicators.md`. Script: `scripts/test_indicators.py`.
Raw: `results/indicators_*.csv`. Each library was compared with reference formulas written from the published
definitions (no library calls), on AAPL, KO, AMC, INTC, SPY daily and MSFT 5-minute.

Reviewer check: five findings reproduced independently with a separate short script and separately written
formulas — CCI bug (source line read), Bollinger width ratio = 1.02598 = sqrt(20/19) exactly, OBV offset =
first bar's volume exactly (287,741,356 for AAPL), Stochastic `smooth_k` ignored (31.8-point difference),
TA-Lib RSI stuck at 50.0 after a single missing value.

## Result
| Indicator | TA-Lib | pandas-ta (default: uses TA-Lib) | pandas-ta own code (`talib=False`) |
|---|---|---|---|
| SMA, EMA, WMA, ROC, Williams %R | exact | exact | exact |
| RSI(14), ATR(14) | exact | exact | differs for first ~250 bars, then exact |
| MACD(12,26,9) | differs first ~80 bars, then exact | same | exact |
| ADX(14) | differs first ~260 bars, then exact | same | differs first ~285 bars, then exact |
| Stochastic(14,3,3) | exact | exact at defaults — **wrong if `smooth_k` ≠ 3** | exact |
| Bollinger(20,2) | exact | exact | **wrong: bands 2.6% too wide** |
| CCI(20) | exact | exact | **wrong: values in the tens of thousands** |
| OBV | exact | exact | **wrong level** (offset by first bar's volume, first value missing) |
| MFI(14) | exact | exact | **wrong** (ties counted as selling; up to 7.9 points off) |
| VWAP (daily anchor) | n/a | n/a | exact |

## Problems found, most dangerous first
1. **pandas-ta's own CCI is wrong** — a missing pair of brackets: `tp - sma / (c * mad)` instead of
   `(tp - sma) / (c * mad)`. Any CCI-based rule computed this way is meaningless.
2. **pandas-ta gives different Bollinger Bands depending on whether TA-Lib is installed.** Its own code
   uses sample standard deviation; TA-Lib and Bollinger's definition use population. Same call, 2.6% different bands.
3. **pandas-ta ignores the `smooth_k` setting when TA-Lib is installed** (up to 32–37 points off). Invisible at defaults.
4. **One missing price silently corrupts TA-Lib output for the rest of the series:** RSI freezes at exactly
   50.0, ADX freezes, and SMA/EMA/MACD/Bollinger/ATR/Stochastic/MFI stay empty forever. No error is raised.
5. pandas-ta's own OBV and MFI are wrong as above.
6. Start-up differences (RSI, ADX, MACD, ATR): different seeding conventions; they fade after 80–285 bars.
   Only matters with short histories — but intraday strategies that reset daily have exactly that.
7. The two libraries have different default lengths (SMA: 10 vs 30; pandas-ta Bollinger: 5) — always pass lengths explicitly.

## Verdict
**TA-Lib: accurate — keep, with two guards:** clean missing values first, and allow ≥300 bars of warm-up.
**pandas-ta: do not use its own implementations** (4 of 14 indicators wrong). If used at all, only with
TA-Lib installed and non-default parameters double-checked. The final repo uses TA-Lib or explicit formulas.
