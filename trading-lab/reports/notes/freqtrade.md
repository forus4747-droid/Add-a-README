# freqtrade 2026.10 (ccxt 4.5.92, Python 3.12) engine accuracy notes

Files: adapters/freqtrade_common.py (shared helpers), adapters/freqtrade_S1.py, adapters/freqtrade_S2.py.
Run: `/home/user/trading-stack/envs/freqtrade/bin/python adapters/freqtrade_S{1,2}.py` from trading-lab/.
Mechanics: data -> feather files in /tmp/ft_S*_xxxx/user_data/data/binance/AAPL_USD-5m.feather (via freqtrade's own
FeatherDataHandler.ohlcv_store); strategy source is written by the adapter to user_data/strategies; config written as JSON;
run with the Python API (`Configuration(...).get_config()`, `Backtesting(config)`, `load_bt_data()`,
`backtest_one_strategy()`), fully offline. Trades read from the engine's result DataFrame (open_date, open_rate,
close_date, close_rate, amount, profit_abs). Temp dir is deleted at the end. pyarrow was already installed (nothing installed).
pnl_net = freqtrade's own `profit_abs` (includes fee 0.0005 on both sides, config `"fee": 0.0005`); no post-processing
besides timestamp formatting (UTC -> America/New_York for S1, synthetic -> real date for S2) and int cast of `amount`.
Config: dry_run, spot, stake_currency USD, stake_amount 10000 (fixed), dry_run_wallet 1e12, max_open_trades -1, minimal_roi
{"0":1000}, stoploss -0.99 (never hit; all 9304 + 179 trades have exit_reason exit_signal), 0 rejected trades.

## Result
S1: PASS (ref 9304 / engine 9304, all mismatch counts 0, max_abs_pnl_diff 5.0e-07, total pnl -83953.18 both)
S2: PASS (ref 179 / engine 179, all mismatch counts 0, max_abs_pnl_diff 5.0e-07, total pnl 54050.15 both)
S1 backtest takes about 5 minutes (254k candles x 30 pairs after gap filling); S2 seconds.

## Questions settled (verified on the installed version)
1. Offline markets. Plain `freqtrade backtesting` with exchange binance fails offline: Exchange.__init__(validate=True) calls
   reload_markets(True) (freqtrade/exchange/exchange.py ~l.332) -> ccxt load_markets -> GET https://api.binance.com/api/v3/exchangeInfo.
   Observed: 3 retries, "Could not load markets", then "Could not load markets, therefore cannot start"
   (validate_stakecurrency). There is no config option that skips this (backtesting always builds a real Exchange and uses
   markets for precision, min stake, fee, pair validation). Not impossible, though: minimal workaround in
   freqtrade_common.install_offline_markets(): monkeypatch only `fetch_markets` and `fetch_currencies` of the async ccxt class
   (the two HTTP calls) to return 30 synthetic spot markets "AAPL/USD" etc. ccxt's load_markets()/set_markets() and all
   freqtrade code run unmodified. Synthetic market: precision amount = 1.0, price = 1e-8 (ccxt precisionMode for binance is
   TICK_SIZE=4), limits amount min 1, taker/maker fee 0.0005, active spot. Exchange name "binance" is just a container.
   Any other outbound access is not used (data is local, no downloads).
2. 24/7 candle assumption. `Backtesting.load_bt_data` -> `history.load_data(..., fill_up_missing=default True)` ->
   `ohlcv_fill_up_missing_data` (data/converter/converter.py) fabricates volume-0 flat candles (open=high=low=close=previous
   close) for every missing timeframe slot; no config switch (the call in backtesting.py l.~366 does not pass the argument).
   Log: "Missing data fillup for AAPL/USD, 5m: before 47333 after 254394 (+437%)".
   - S1: harmless if handled in the strategy. Fake rows exist only outside 09:30-15:55 (and for missing bars, whose days have <78 real bars
     and are skipped). Signals are only generated on real rows in 10:00-15:50 whose next row is the next real bar. The strategy
     counts real bars as rows with volume > 0 (min real volume in data is 40, verified) for the 78-bar rule and ORB.
     Cost: ~4.4x more rows, hence the 5-min runtime.
   - S2 (1d): NOT harmless. Weekend/holiday gaps become fake daily rows, a Friday signal executes at the fake Saturday row
     (price = Friday close) and SMAs include flat fake days. Measured with `freqtrade_S2.py --naive` (real UTC midnight dates, same
     strategy, writes results/trades/freqtradenaive_S2.csv): 284 trades vs 179 reference, 178 missing, 283 extra, total pnl
     36505.07 vs 54050.15 (FAIL; also trades dated on Sundays). Workaround used by default: store the daily bars on a
     gap-free synthetic calendar (k-th trading day = 2000-01-03 + k days, per symbol) so freqtrade has nothing to fill, then map
     the synthetic dates of freqtrade's trades back to real trading dates (timestamp reformatting only). This is a data-layout trick, not an engine change.
3. Signal timing. freqtrade shifts signals by one row (`_get_ohlcv_as_lists`, shift(1)) and fills at the next row's open
   (`_get_close_rate` for exit_signal returns row open; entry uses row open): signal on candle N fills at candle N+1 open, as required.
   The first row of each pair is dropped (`df_analyzed.drop(head(1))`) and no entry is allowed on the last row; neither affects
   these strategies (no signal possible on first row; S1 last row is a 15:55 exit).
4. Whole-share sizing: achievable and exact. `_enter_trade`: amount = stake/open_rate, then `amount_to_contract_precision(...,
   precision_amount=1.0, TICK_SIZE)` truncates to whole units -> floor(10000/fill_price). No custom_stake_amount needed; shares_mismatch = 0
   over 9483 trades. Price precision is 1e-8 and freqtrade additionally derives tick size from the data (`get_tick_size_over_time`);
   prices come out unrounded (entry/exit price mismatches 0). Wallet is made huge so the 10000 stake is never limited.
5. Fee: config `"fee": 0.0005` applied to open and close (Backtesting.set_fee); profit_abs = amount*close*(1-fee) - amount*open*(1+fee).
   Matches the protocol formula to 5e-7.
6. Time of day / DST: candle dates are UTC candle-open; the strategy converts with `df.date.dt.tz_convert("America/New_York")` and
   derives day and HH:MM from it (both EST and EDT periods are in the data); output times are converted back the same way.
   Zero time mismatches over 9304 trades, so DST is handled.
7. S1 state logic (one trade/day, stop only while long): "first breakout bar of the day" is precomputed in pandas as the only
   enter_long; exit_long is set on stop bars (10:00-15:50 close < range low; the 15:40 cutoff applies to entries only) and on the 15:50 bar
   (executes at the 15:55 open = rule 4). freqtrade ignores exit flags while flat and entry flags while a position is open. Fills, share counts and P&L are the engine's.
8. S2 end-of-window rule. Native behaviour: `Backtesting.handle_left_open` closes remaining trades with exit_reason "force_exit" at
   the OPEN of the last data row (`exit_row[OPEN_IDX]`), not the close, and dated the last day. Protocol wants the last day's close.
   Difference if used natively: 20 positions were still open at 2025-12-31; closing at open instead of close would change total
   gross pnl by +1395.83 USD (computed from the daily bars: sum shares*(open-close)), i.e. up to ~$100 per trade (e.g. IBM 301.76 vs 296.20).
   Workaround used: append one sentinel row after the last real day with open=high=low=close=last day's close and volume 0; the strategy
   emits exit_long on the last real day (and suppresses entries on it), so freqtrade's normal exit-signal machinery fills at the sentinel's open (= last close).
   The sentinel's date is reported as the last real day (2025-12-31). Exit price/pnl come from freqtrade; this is a data/signal device (same idea as vectorbt's sentinel).
   Side effect: a cross signal on the last real day does not open a trade (it would fill at the "next" day, which does not exist) - the protocol has no such trade either.
9. SMA warm-up: startup_candle_count left at 0 so freqtrade does not trim; rolling(20/50) give NaN early, comparisons are False, no signals until SMA50 exists. Matches the reference.

## Deviations / limitations (all remaining ones are zero in the results)
- Offline markets need the ccxt fetch_markets/fetch_currencies monkeypatch (item 1).
- Gap filling cannot be turned off; S1 tolerates it (volume>0 mask), S2 needs the synthetic gap-free calendar (item 2).
- Native end-of-backtest force exit is at the last candle's open; replaced by the sentinel row (item 8).
- Fractional-share behaviour is a precision setting of the (fake) market, not a freqtrade stake option; whole shares exact.
- Not covered: timeframe_detail, protections, position adjustment (not used).

## Reviewer double-checks
- That the monkeypatched market metadata (precision amount 1.0) is acceptable as "legit minimal workaround".
- Sentinel row for S2 (item 8) and synthetic calendar (item 2) are adapter-side data tricks; both are documented and the naive variant proves why.
- results/trades/freqtradenaive_S2.csv and results/compare_freqtradenaive_S2.json are by-products of the naive experiment, not a result.
