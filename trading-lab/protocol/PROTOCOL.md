# Test Protocol (frozen before any backtest was run)

Written 2026-11-13, committed before Step 2. Any later change must be a new commit that says why.

## 1. Data
- Source: Alpaca market data API, `feed=sip`, `adjustment=split`, 5-minute bars, regular hours only
  (09:30–15:55 New York bar start times). Fetched by `scripts/fetch_data.py`.
- Universe: 30 symbols — AAPL AMGN AXP BA CAT CRM CSCO CVX DIS DOW GS HD HON IBM INTC JNJ JPM KO MCD MMM MRK
  MSFT NKE PG TRV UNH V VZ WBA WMT. (WBA ends 2025-08-27, delisted.)
- Same data as the Drive folder "Day Trader Backtest Data" (spot-checked row-for-row on MSFT and HON 2023).
- Files are not committed (135 MB). `reports/01_data_manifest.csv` holds a sha256 for every file.

## 2. Time splits — the "no peeking" rule
| Split | Dates | Used for |
|---|---|---|
| DEV | 2023-08-01 → 2024-12-31 | building, fitting, debugging |
| VAL | 2025-01-01 → 2025-12-31 | comparing repos; out-of-sample for anything fitted on DEV |
| SEALED | 2026-01-01 → 2026-11-12 | final skill only, run once, in Step 5 |

- SEALED files live in `data/sealed_2026/` with permissions `000`. No script in Steps 1–4 reads them.
- Any model that learns (Qlib, FinRL, the final skill) is fitted on DEV only, and scored on VAL.
- Signals may only use bars that have fully closed. Orders fill at the NEXT bar's open.

## 3. Benchmark strategies (fixed rules, no tuned parameters)
Both are long-only, one position per symbol, each symbol traded independently.
Position size: `shares = floor(10000 / fill_price)` (whole shares).
Cost: 0.05% of traded value per side (covers commission + slippage).

**S1 — Opening-range breakout (day trade, 5-min bars)**
1. Opening range = highest high and lowest low of the six bars 09:30–09:55.
2. From the 10:00 bar through the 15:40 bar: if flat, no trade yet today, and bar close > range high → buy at next bar's open.
3. If long and bar close < range low → sell at next bar's open.
4. If still long, sell at the open of the 15:55 bar.
5. At most one trade per symbol per day. Days with fewer than 78 bars (half days, gaps) are skipped.

**S2 — 20/50-day moving-average cross (swing, daily bars)**
1. Daily bars built from the 5-min bars: open = first open, high = max, low = min, close = last close, volume = sum.
2. SMA20 and SMA50 of daily close.
3. If flat and SMA20 > SMA50 at day t's close, and SMA20 <= SMA50 at day t-1's close → buy at day t+1's open.
4. If long and SMA20 < SMA50 at day t's close → sell at day t+1's open.
5. Open positions at the end of the test window are closed at the last day's close.

## 4. What "accurate" means, per repo type
| Type | Repos | Test | Pass mark |
|---|---|---|---|
| A. Backtest engine | backtesting.py, Backtrader, vectorbt, NautilusTrader, Zipline, Freqtrade, Jesse, vn.py, LEAN | Run S1/S2, compare trade list to the reference (Step 2) | same trades; entry/exit times identical; net P&L within $0.01 per trade |
| B. Data / indicators | TA-Lib, pandas-ta, yfinance, OpenBB | Compare output to hand-computed values / our Alpaca data | indicators within 1e-6; daily closes within 0.5% |
| C. Predictive | Qlib, FinRL, TradingAgents, ai-hedge-fund | Fit on DEV, predict VAL, score vs what really happened | reported as-is: hit rate, return vs buy-and-hold |
| D. Not testable here | ccxt, ib_async, alpaca-py, Hummingbot, OctoBot, ML4T notebooks | reason recorded | — |

## 5. Process rules
- One repo at a time, in the order listed in `reports/00_INDEX.md`.
- For each repo: write adapter → run → compare → record every mismatch → find the cause → fix or mark as a
  real limitation → commit report + raw results. No repo's result is edited after seeing another repo's.
- Every number in a report comes from a file in `results/` produced by a script in this repo.
