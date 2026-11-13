# Rules for writing an engine adapter (engine accuracy test)

Goal: make ENGINE run strategies S1 and S2 exactly as written in `protocol/STRATEGIES.md`, using the
engine's own order/fill machinery, and export its trades. Then compare with the reference.

## You MUST
1. Read `protocol/STRATEGIES.md` and `lab/data.py` first.
2. Write `adapters/ENGINE_S1.py` and `adapters/ENGINE_S2.py`. Each, run from the `trading-lab/` folder with the
   given python, writes `results/trades/ENGINE_S1.csv` / `ENGINE_S2.csv` with exactly these columns:
   `symbol,entry_time,entry_price,exit_time,exit_price,shares,pnl_net`
   - S1 times: New York local time `YYYY-MM-DD HH:MM` (the bar whose open filled the order). S2 times: `YYYY-MM-DD`.
   - `pnl_net` = profit after the 0.05%-per-side cost, taken from the engine's own accounting where possible.
3. Load data only through `lab.data.load_5min(sym)` (S1) and `lab.data.daily_from_5min(sym)` (S2), all 30 `lab.data.DOW` symbols.
4. Trades must be produced BY THE ENGINE (its broker/fill simulation). Signals may be computed in the engine's
   strategy callback or precomputed with pandas, but entries, exits, share counts and fills must come from the engine.
5. Check yourself with: `PY scripts/compare_trades.py ENGINE S1` (and S2). Iterate until PASS or until you can
   prove the remaining difference is a real limitation of the engine.
6. Write `reports/notes/ENGINE.md`: every problem you hit, its cause (cite engine file/function or doc), how you
   fixed it or why it cannot be fixed, and the final compare output for S1 and S2. Facts only.

## You MUST NOT
- Read, import or copy anything from `reference/` or `results/trades/reference_*.csv` in adapter code.
  (You may look at unmatched trades printed by the compare script to debug.)
- Edit anything outside `adapters/ENGINE_*`, `results/trades/ENGINE_*`, `reports/notes/ENGINE.md`.
- Change the strategy rules, costs or sizing to force a match. If the engine cannot do something, say so.
- Hard-code trades, post-edit the CSV by hand, or patch numbers after the engine has run.
  Allowed post-processing: reformatting timestamps, and computing pnl_net from the engine's fill prices and
  share counts with the protocol's fee formula if the engine does not expose per-trade net P&L (say so in notes).
- Install packages other than ones the engine itself needs (say which in notes). No git commands. No network
  access other than pip. Do not touch `/home/user/trading-stack/data`.
- Spend more than ~40 minutes. If stuck, stop and report honestly what works and what does not.

## Final message
Reply with: PASS/FAIL for S1 and S2, the list of problems found, and anything a reviewer should double-check.
