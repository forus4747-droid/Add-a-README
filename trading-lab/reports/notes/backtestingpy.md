# backtesting.py (v0.6.6) engine accuracy notes

Adapters: `adapters/backtestingpy_S1.py`, `adapters/backtestingpy_S2.py`. One `Backtest` per symbol, 30 DOW symbols.
S1 runtime about 16 s for all 30 symbols (about 1.4M bars); S2 a few seconds.
Settings: `trade_on_close=False`, `hedging=False`, `exclusive_orders=False`, `cash=1e9`, `commission=<callable>`. No extra packages installed.
Entries and exits are `Strategy.buy()` and `position.close()`; fills, share counts, entry/exit prices and times come from the engine (`stats._trades`).
Signals: S1 range high/low, bar-count validity and time-of-day are precomputed with pandas and passed as extra data columns; the entry/exit decisions are in `next()`. S2 uses `self.I` SMA(20/50) computed from closes.

## Problems and causes

1. Sizing floor(10000/fill_price) with unknown fill price.
   Cause: `Strategy.buy(size=int)` fixes the share count at order time, when the next open is unknown. Size in (0,1) is a fraction of
   available margin and is converted at fill time (`_Broker._process_orders`, backtesting.py: `size = int((margin_available * leverage * abs(size)) // adjusted_price_plus_commission)`).
   Fix: while flat, equity == cash, so I pass `size = (10000/equity)*(1+1e-12)` (budget of $10,000 at the real fill price; always < 1 because cash is 1e9).
   The engine then computes `int(10000 // open)` itself. The 1e-12 factor guards float rounding.
   Without the factor (I first used `1-1e-12`) 6 trades with an exactly integer 10000/price (e.g. 500.00, 20.00) got one share fewer.
2. Commission contaminates the sizing.
   Cause: the same line divides by `price + commission(order.size, price)/abs(order.size)`, so a relative `commission=0.0005` yields floor(10000/(p*1.0005)), which differs from the protocol.
   Fix: `commission` accepts a callable `(order_size, price)` (documented; `_Broker._commission_func`). The callable returns 0 when `abs(order_size) < 1`
   (the sizing call with the fractional size) and `abs(size)*price*0.0005` for real fills (integer size, charged at entry and exit via `_open_trade`/`_close_trade`).
   Net P&L is the engine's own `PnL` column in `stats._trades` (includes both commissions); no recomputation.
3. S1 exit rule scope (protocol reading, not an engine fault). With rule 3 limited to the 15:40 bar, 22 trades exited at 15:55 where the
   reference exited at 15:50 (signal on the 15:45 bar). Reading rule 3 literally (exit check on every bar while long; only entries restricted to 10:00-15:40 bars; rule 4 closes on the 15:50 bar) matches. Entries after 15:40 are not allowed.
4. S2 "close open positions at the last day's close" cannot be done natively.
   Cause: market orders fill at next bar's open; `finalize_trades=True` closes the remaining trades with `trade.close()` and re-runs the broker on the SAME last bar, so the fill is at the last bar's OPEN (backtesting.py `Backtest.run`, finalize block + `_process_orders`). That gave 21 exit-price mismatches (max pnl diff $200.06; total pnl 55373.79 vs 54050.15).
   Fix (workaround, a data-side device): append one sentinel bar (date = last date + 1 day, O=H=L=C= last real close, volume 0). On the last real bar the strategy closes any open position; the engine fills it at the sentinel's open (= last close). The exit time is mapped back to the last real date in post-processing. The strategy places no entries on the last real day or on the sentinel.
   `trade_on_close=True` is not usable since it would also fill the entries at the previous close.

## Final compare output
S1: PASS. ref_trades 9304, engine_trades 9304, missing 0, extra 0, exit_time/entry_price/exit_price/shares mismatches 0, pnl mismatches >1c 0, max_abs_pnl_diff 5.0e-07, total pnl -83953.18 both.
S2: PASS. ref_trades 179, engine_trades 179, missing 0, extra 0, all mismatches 0, max_abs_pnl_diff 5.0e-07, total pnl 54050.15 both.

## Reviewer should double-check
- The fractional-size sizing trick and the callable-commission trick (items 1, 2): the engine does the sizing, but only because of those inputs.
- The S1 rule 3 reading (item 3) and the S2 sentinel bar (item 4).
- Sizing equals floor(10000/price) except if 10000/price lies within about 1e-12 (relative) below an integer; none found in these data.
