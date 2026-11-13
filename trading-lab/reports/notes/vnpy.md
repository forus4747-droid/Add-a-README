# vnpy (VeighNa) engine accuracy notes

Engine: vnpy 4.5.0 core (`vnpy`) has NO backtester (no backtesting module in `vnpy/trader`). The CTA backtester is the separate
package `vnpy_ctastrategy` 1.4.1 (`vnpy_ctastrategy/backtesting.py: BacktestingEngine`, `template.py: CtaTemplate`).
Adapters: `adapters/vnpy_S1.py`, `adapters/vnpy_S2.py`, shared `adapters/vnpy_common.py`. One BacktestingEngine run per symbol, 30 DOW symbols.
Runtime: S1 about 11 s, S2 about 3 s.

## Installed
- `VIRTUAL_ENV=.../envs/vnpy uv pip install vnpy_ctastrategy` -> installed exactly one package: `vnpy-ctastrategy==1.4.1` (all 42 other deps, incl. PySide6, plotly, pandas, were already present).
- pyarrow NOT installed: `lab/data.py` imports only pandas at module level; `load_daily` (the only user of parquet) is not used by the adapters.
- Import works headless with `QT_QPA_PLATFORM=offscreen` (set via `os.environ.setdefault` in vnpy_common.py before importing; vnpy_ctastrategy/__init__ pulls in the UI package). Not strictly tested without it.

## Findings (verified in source)
1. Order model. `BacktestingEngine.new_bar` -> `cross_limit_order()` runs BEFORE `strategy.on_bar` of the new bar, so an order sent in on_bar(t) is first tested on bar t+1.
   Long fill: requires `order.price >= bar.low`, trade price `min(order.price, bar.open)`; short: `order.price <= bar.high`, price `max(order.price, bar.open)`.
   So a marketable limit (buy at 1e7, sell at 1e-6) fills EXACTLY at the next bar's open (and always crosses). Verified: 0 entry/exit price mismatches.
2. Costs. `rate=0.0005, slippage=0, size=1, pricetick=1e-6` (round_to uses Decimal; fills use the unrounded bar open, so tick does not alter fill prices; data min price ~$1+ anyway).
   The CTA engine does NOT put commission on trades. It is only computed per day in `DailyResult.calculate_pnl` (turnover*rate), aggregate not per trade.
   So per-trade `pnl_net` = (exit-entry)*shares - 0.0005*shares*(entry+exit) from engine fill prices/volumes (allowed post-processing). Cross-check on AAPL S1:
   sum of my round-trip pnl_net = -4373.0337 equals engine `calculate_result().net_pnl.sum()` = -4373.0337 (engine commission 3255.46).
3. Sizing floor(10000/open) unknown at order time. `CtaTemplate.buy(price, volume)` fixes volume at send time and the engine fills `order.volume`.
   Legit approach used: `cross_limit_order` calls `strategy.on_order(order)` (status SUBMITTING -> NOTTRADED) for each active order on the new bar BEFORE the cross test, and `engine.bar` is already the new bar. In `SizedTemplate.on_order` I set `order.volume = floor(10000/engine.bar.open_price)` (the actual fill price, no look-ahead). The engine then fills that volume.
   This relies on mutating the engine's OrderData inside a callback (an engine-internal detail, not a documented API). Without it, sizing from the signal bar close would differ in 120 of 9304 S1 entries (1.3%) (measured, not used).
4. Daily vs intraday / timezones. Bars are fed by assigning `engine.history_data = [BarData...]` (`load_data()` not called, so no database). `engine.interval` only matters for load_data; S1 uses Interval.MINUTE, S2 Interval.DAILY.
   Bar datetimes are naive New York local times from `time_new_york`; the engine does no tz conversion on fed bars, so `bar.datetime.hour/minute` gives New York clock time directly (no DB_TZ involvement). S1 rules use minutes-since-midnight (10:00=600, 15:40=940, 15:50=950).
   Days with <78 bars: day-length is a pre-computed data fact (pandas) passed to the strategy because the bar count is not known at 09:55.
   Rule 3 read as the other adapters did (exit check on every bar while long, entries only <=15:40; rule 4 at the 15:50 bar -> 15:55 open); consistent with the 2026-11-13 clarification.
5. S2 "close at last day's close". The engine only fills at the next bar's open and fills nothing on the last bar. Workaround (data-side device, same as backtesting.py adapter): append one sentinel daily bar (last date + 1 day, O=H=L=C = last real close, volume 0). On the last real bar the strategy sends the exit; the engine fills at the sentinel open = last close; the exit date is mapped back to the last real date in post-processing. No entries are sent on the last real day. This is not native engine behaviour.
6. Round trips. `engine.get_all_trades()` returns individual fills; with one long-only position they alternate BUY/SELL and are paired in order (asserts check direction/volume and that nothing is left open).
7. Signals are computed inside the strategy `on_bar` (range, SMA20/50 from stored closes); entries, exits, volumes, fill prices and times come from the engine.

## Final compare output
S1: PASS. ref_trades 9304, engine_trades 9304, missing 0, extra 0, exit_time/entry_price/exit_price/shares/pnl mismatches 0, max_abs_pnl_diff 5.0e-07, total pnl -83953.18 both.
S2: PASS. ref_trades 179, engine_trades 179, missing 0, extra 0, all mismatches 0, max_abs_pnl_diff 5.0e-07, total pnl 54050.15 both.

## Reviewer should double-check
- The on_order volume rewrite (item 3) and the sentinel bar (item 5): both are workarounds around what the engine natively does.
- The strategy does hold a pending-order assumption: buy/sell limits always cross (never cancelled); verified by asserts in pairing (no open/odd fills).
