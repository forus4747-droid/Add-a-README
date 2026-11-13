# jesse — engine accuracy test (S1, S2)

Engine: jesse 3.6.1 (`/home/user/trading-stack/envs/jesse`), `jesse.research.backtest`. Files: `adapters/jesse_common.py`,
`adapters/jesse_S1.py`, `adapters/jesse_S2.py`. No package installed (pyarrow not needed: `lab/data.py` imports it only in `load_daily`, unused here).

## Final compare output
S1: ref_trades 9304, engine_trades 9304, missing 0, extra 0, exit_time/entry_price/exit_price/shares mismatch 0, pnl_mismatch_over_1c 0,
max_abs_pnl_diff 5.0e-07, total pnl -83953.18 both -> **PASS** (all 30 symbols, ~2m10s).
S2: ref 179, engine 179, all mismatches 0, max_abs_pnl_diff 5.0e-07, total pnl 54050.15 both -> **PASS**.
`pnl_net` is jesse's own closed-trade `PNL` (net of its fee); no post-processing other than timestamp formatting.

## Facts about the engine (verified in installed source)
1. **No DB / redis / network needed for research mode.** `jesse/research/backtest.py::backtest()` takes numpy candles; redis is not even
   installed in the env and the run works. (The normal `jesse backtest` CLI path `modes/backtest_mode.py::load_candles` uses the database; not used.)
2. **1-minute base candles, gaps.** `backtest()` requires 6-column rows `[ts, open, close, high, low, volume]`, minute-aligned, strictly increasing
   (`candle_service.validate_observed_one_minute_candles`). In 3.6.1 it does NOT require contiguity: `backtest_mode._uses_observed_timestamp_replay`
   selects `_timestamp_simulator` when `np.diff(ts) != 60_000`, which replays only observed rows by timestamp and builds higher timeframes with
   `generate_completed_candles_from_observed_minutes` (clock-aligned buckets, empty buckets simply absent). So overnight/weekend gaps need no filler
   candles (the old dense `_validate_contiguous_one_minute_candles` exists but is not called by `backtest()`). Older jesse versions would differ; this is 3.6.1 behaviour.
3. **Our bars are 5-minute, not 1-minute. Workaround (not native):** each bar is fed as TWO "1m" rows: row A at bar open T = flat opening print
   (o=h=l=c=bar open, volume 0); row B at T+1min = (open=bar open, close, high, low = bar's, volume = bar's). Jesse's own aggregation of A+B into a
   5m (or 1D) bucket reproduces the original bar OHLCV exactly (checked: printed 5m candles equal source bars). This is lossless for OHLCV and for a
   strategy that acts only on opens/closes, but the intra-bar path is invented (flat open, then the whole range in one minute); any limit/stop order resting
   inside a bar would see that fictitious path. Not used here: only market orders. 5 synthetic minutes per bar was not needed.
4. **Order fill timing (native).** A market order fills at `position.current_price` = close of the latest 1m row at the moment the strategy runs
   (`services/broker.py::buy_at_market` passes `position.current_price`; `Strategy.liquidate()`/`reduce_position_at` use `self.price` = close of
   the current candle; `execute_simulated_market_orders` fills immediately in the same event). So natively a decision at a bar's close fills AT THAT CLOSE, not the next
   open. Probe (AAPL 2023-08-01, dense 5x1m candles per bar, route 5m, buy on bar index 20): fill 195.885 = bar close (next open was 195.86). Same on a 1m route fed one row per bar.
   There is no "next-bar-open" market-order mode. **Workaround used:** the strategy route is `1m`, acts only on row-A events (`ts % 5min == 0` for S1, `ts % 1day == 0` for S2),
   reads the just-completed 5m / 1D bar from jesse's own data-route candles (`k[-2]`; `k[-1]` is the forming bucket), and submits a MARKET order; at that event
   the current price is the opening print, so jesse's broker fills at the bar's open. The fill price is genuinely produced by jesse's broker, but the "next open" semantics come
   from my data layout (opening-print row), not from an engine feature. Fill timestamps are stamped end-of-row (T+60s); the adapter subtracts 60 s to get the bar open time.
5. **Fees.** `fee=0.0005` in config; `order_service.execute_order`: `fee = fee_rate * |qty| * price` per order (both sides) = protocol cost. Used `type: futures`, leverage 1,
   balance 1e9. Reason: `type: spot` (`models/SpotExchange.py` lines ~99/111) deducts the buy fee from the received base quantity (`qty*(1-fee)`), which would change
   share counts/PnL vs the protocol. Futures model: perpetual `funding_rate` is only an exposed attribute, not applied to backtest P&L (grep of `jesse/`). The "futures" label is a modelling shortcut for stocks.
6. **Sizing.** `qty = floor(10000/self.price)` in `go_long`, where `self.price` is the opening print of the fill bar (= fill price). Shares matched on all trades.
7. **S2 daily bars / UTC alignment.** Jesse `1D` buckets are UTC-day clock buckets (`ts // 86_400_000`). A US session (13:30-21:00 UTC) never straddles UTC midnight, so
   our daily bar for date D is placed at 00:00 UTC of D (rows A/B at 00:00 and 00:01) — a relabelling of the timestamp, not a data change. Representable: yes. Jesse's `1D` bar = our daily bar.
   SMA via `jesse.indicators.sma` on completed 1D candles. Last-day close-out: jesse's `Strategy._terminate` closes an open position at `position.current_price` (last candle close = last day's close, fee charged) — matches rule 4.
8. **Other implementation details.** S1 "days with <78 bars skipped" and the day/minute-of-day of each bar are precomputed with pandas (allowed: signals may be precomputed) and passed via module globals; the range/breakout/exit logic runs in the strategy callback; entries, exits, sizes, fills, fees come from jesse.
   One backtest per symbol (independent symbols, balance 1e9, so no cash interaction).

## Problems hit
- Fill at bar close instead of next open (item 4) — fixed by layout/trigger-on-opening-print workaround; cannot be fixed natively.
- Jesse's `liquidate()` would also fill at the decided bar's close; with the opening-print trigger it fills at the open. Verified by exact match of all 9304 + 179 trades.
- Naive one-row-per-bar probe with route `5m` produced 0 trades in my probe (not investigated further); with route `1m` fills were at bar close (item 4).

## Things a reviewer should double-check
- That the opening-print workaround (item 3/4) is acceptable as "engine-produced" fills; it relies on a synthetic flat row, and on 3.6.1's sparse-timestamp replay.
- The 'futures' simulation model used to get per-side notional fees.
- Match was exact (max pnl diff 5e-7), so no tolerance masking.
