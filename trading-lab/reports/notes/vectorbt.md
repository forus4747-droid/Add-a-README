# vectorbt 1.0.0 engine accuracy notes

Adapters: adapters/vectorbt_S1.py, adapters/vectorbt_S2.py. Both use vbt.Portfolio.from_signals
(direction="longonly", price=open series, size=floor(10000/open) per bar with size_type="amount", fees=0.0005,
init_cash=1e9, accumulate=False). Trades read from pf.trades.records_readable; pnl_net is vectorbt's own "PnL"
(includes entry and exit fees). No post-processing besides timestamp formatting and share count int cast. No extra packages installed.

## Problems
1. S1 first run: 22 trades exited at 15:55 instead of 15:50 (exit_time/price/pnl mismatches, max pnl diff $56.67).
   Cause: my own reading error. I limited the stop (rule 3) to 10:00-15:40 bars; STRATEGIES.md applies the
   10:00-15:40 window only to entries (rule 2). Stop signals on the 15:45 bar execute at the 15:50 open.
   Fix: stop signals from any bar 10:00-15:50 (15:55 excluded, its signal would execute on next day's first bar).
   Not an engine limitation.
2. S2 end-of-window rule (open position closed at last day's close): from_signals fills only at the price array.
   Handled by appending one sentinel row after the last day whose price = last day's close, with an exit signal;
   exit_time is reported as the last day's date. Fill still produced by vectorbt. Open trades (Status "Open") would
   otherwise be marked to the last price rather than closed; the adapter asserts all trades are Closed.
3. State handling in S1 (one trade/day, stop only when long): encoded in pandas (only first breakout bar per day is
   an entry; exits are ignored by vectorbt when flat, which matches "stop only matters while long"). Entry and exit
   signals can never coincide on a bar (close>high vs close<low; forced exit at 15:55 is never an entry bar).
   No vectorbt ignore/conflict behaviour altered results.

## Final compare output
S1: PASS (ref 9304 / engine 9304 trades, all mismatch counts 0, max_abs_pnl_diff 5.0e-07, total pnl -83953.18 both)
S2: PASS (ref 179 / engine 179 trades, all mismatch counts 0, max_abs_pnl_diff 5.0e-07, total pnl 54050.15 both)
