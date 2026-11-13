# nautilus_trader accuracy notes (S1, S2)

Engine: nautilus_trader 1.231.0 (/home/user/trading-stack/envs/nautilus), pandas 3.1.1 already present, nothing installed.
Files: adapters/nautilus_common.py (harness), adapters/nautilus_S1.py, adapters/nautilus_S2.py.
Runtime: S1 ~39 s, S2 ~2 s (one BacktestEngine per symbol, 4 processes).

## Design
Low-level BacktestEngine, venue SIM, CASH account, NETTING, one `Equity` per symbol (lot_size 1, taker/maker fee 0.0005,
default MakerTakerFeeModel => 0.05% of notional per fill, market orders are TAKER).
Venue is fed ONLY QuoteTicks with bid=ask=bar open (`bar_execution=False`). The strategy gets Bars (ts_init = bar close
time = open+5min; daily bars: last 5-min bar open+5min) for signals via on_bar. The open quote of bar N+1 is stamped
(open time + 1 ns), i.e. just after bar N's close, so on_bar(N) always runs before the quote. On that quote
(on_quote_tick) the strategy submits the market order; the matching engine already holds that quote, so the order
fills at the open, and shares = floor(10000/ask) is computed from the known open. Fills/positions/commissions come from
the engine. 15:55 exit and S2 "close at last day's close" use the same mechanism (S2: one extra synthetic quote at last
day's close ts+1ns, used only for the final forced sell).
Timestamps: fill ts (UTC ns, minus nothing; the +1ns is invisible at minute resolution) converted to America/New_York.

## Problems / findings
1. Bar execution fills at the SAME bar's close, not the next open. Verified with a 3-bar test (bar_execution=True, order
   submitted in on_bar of bar 1 filled at bar 1 close 10.5, ts = bar-1 close). Cause: the matching engine, when a bar is
   processed, updates its book from the bar's O/H/L/C and a market order submitted on the bar event executes against the
   current (close) price. So the protocol's next-open fill cannot be had from bars directly. Workaround: open-price
   quote ticks as above (documented, this is what the "open event" substitute is). No strategy rule changed.
2. Sub-cent prices: data has prices such as 187.845, 175.4579. Instrument price_precision=2 silently rounded fills
   (2803 entry-price mismatches first run). Fixed with price_precision=6 (PREC in nautilus_common.py).
3. pandas 3.x: `astype("int64")` on datetimes gives microseconds (not ns) -> wrong timestamps (1970 dates). Fixed with
   `.dt.as_unit("ns")`.
4. Engine money precision: realized_pnl and commissions are Money(USD) rounded to 2 dp per fill, so the engine's own
   `realized_pnl` differs from exact fee math by up to ~0.015 per trade (230 trades > 1c in S1; S2 max 0.009).
   Therefore pnl_net is computed from the engine's fill prices (position avg_px_open/avg_px_close) and share count
   (peak_qty) with the protocol formula (exit-entry)*sh - 0.0005*sh*(entry+exit). The engine's rounded value is kept in
   `pnl_engine` internally but not written. Fill prices, shares, times are the engine's.
5. S1 exit window: first run applied the 10:00-15:40 window to the stop exit too (step 3 has no window in the text);
   22 trades exited at 15:55 instead of 15:50 (stop signal on 15:45 bar close). Step 3 text has no window, so the stop
   is now checked on every bar from 10:00; entries remain limited to <=15:40. This is a reading of the protocol (ambiguity),
   not a number fit; reviewer should confirm that is the intended meaning.
6. Positions report timestamps (ts_opened/ts_closed) are tz-aware datetimes; used pd.Timestamp(...).value.

## Final compare output
S1: PASS  ref_trades 9304, engine_trades 9304, missing 0, extra 0, exit_time/entry_price/exit_price/shares mismatch 0,
pnl_mismatch_over_1c 0, max_abs_pnl_diff 5.0e-07, total pnl ref -83953.18 / engine -83953.18.
S2: PASS  ref_trades 179, engine_trades 179, all mismatches 0, max_abs_pnl_diff 5.0e-07, total pnl ref 54050.15 / engine 54050.15.
(results/compare_nautilus_S1.json, results/compare_nautilus_S2.json)
