# Step 2 — Reference backtester, scoring harness, baselines

## 2a. Reference backtester (ground truth for the engine test)
- Code: `reference/ref_backtest.py` — plain Python loops, one bar at a time, no backtest library.
- Proof it is right: `tests/test_reference.py`, 6 cases whose expected trades and P&L are worked out by hand
  in the comments (e.g. 98 shares, +$185.906 net). Run: `pytest tests/test_reference.py` → 6 passed.
- Run on real data by `scripts/run_reference.py` → `results/trades/reference_S1.csv`, `reference_S2.csv`.

| Strategy | Window | Trades | Net P&L | Win rate |
|---|---|---|---|---|
| S1 opening-range breakout | 2023-08-01 → 2025-12-31, 30 Dow stocks | 9,304 | −$83,953.18 | 42.6% |
| S2 20/50 SMA cross | same, daily bars built from 5-min | 179 | +$54,050.15 | 46.4% |

These are the numbers every engine must reproduce. (They are also a first finding: the textbook
opening-range breakout loses money after costs on these stocks.)

## 2b. Scoring harness (for the prediction test)
- Code: `lab/score.py`. Swing target = open[t+1] → open[t+6]. Day target = 10:00 open → 15:55 open.
- Metrics: rank IC, IC t-stat (deflated for overlapping 5-day targets), hit rate, top-minus-bottom
  quintile, top-quintile return net of 0.1% round-trip cost, equal-weight benchmark, excess.
- Verdict rule (fixed in PROTOCOL §3): "PREDICTS" only if IC t-stat > 2 and net excess > 0 on VAL.

## 2c. Baselines (`scripts/run_baselines.py` → `results/02_baselines.csv`)
| Task | Skill | Split | Rank IC | t-stat | Hit rate | Top-quintile net/yr | Equal-weight/yr | Verdict |
|---|---|---|---|---|---|---|---|---|
| swing | random | VAL | −0.0001 | −0.02 | 50.0% | 12.2% | 18.7% | no proven edge |
| swing | 12-1 momentum | VAL | 0.0104 | 0.38 | 50.6% | 9.4% | 18.7% | no proven edge |
| swing | 5-day reversal | VAL | 0.0119 | 0.49 | 50.1% | 32.0% | 18.7% | no proven edge |
| day | random | VAL | 0.0049 | 0.43 | 50.2% | −11.6% | 8.2% | no proven edge |
| day | first-30-min momentum | VAL | −0.0248 | −1.64 | 48.6% | −13.0% | 8.2% | no proven edge |
| day | first-30-min reversal | VAL | 0.0248 | 1.64 | 51.4% | −14.4% | 8.2% | no proven edge |

DEV rows are in the CSV. Things the baselines already teach:
1. **Random scores got t = 2.36 on the 6-month day-DEV window.** So t > 2 on a short window can be luck.
   Consequence: a skill must pass on VAL (a full year), and the final skill must also pass on SEALED.
2. Momentum looked good on DEV 2024 (IC 0.045) and failed on VAL 2025 (IC 0.010) — a textbook
   example of an edge that does not carry forward.
3. Trading intraday every day costs ~25%/yr in fees alone (0.1% × 252). A day-trading skill needs a
   large edge just to break even.
