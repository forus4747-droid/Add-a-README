# backtrader (1.9.78.123) engine accuracy notes

Files: adapters/backtrader_common.py (shared helper), adapters/backtrader_S1.py, adapters/backtrader_S2.py.
No packages installed. pnl_net = `trade.pnlcomm` from backtrader's own accounting (no post-computation).

## Setup used
- One `bt.Cerebro` per symbol, `setcash(1e9)`, `broker.setcommission(commission=0.0005)` (percentage, stock-like, charged per side),
  `set_checksubmit(False)`, `stdstats=False`.
- Data via `bt.feeds.PandasData`. Timestamps = naive New York wall-clock (`time_new_york` parsed with pd.to_datetime, no tz conversion),
  so backtrader never applies tz logic (it treats naive datetimes as UTC-less numbers via date2num; times round-trip exactly). Not feeding `time_utc` avoids any tz shift.
- Sizing on the fill bar's open: `cerebro.run(cheat_on_open=True)` makes backtrader call `Strategy.next_open()` before the broker
  processes the new bar; there data[0] is the new bar (its open is known, used for `floor(10000/open[0])`), data[-1] is the previous bar (signal bar).
  Market orders created in next_open fill at that bar's open (cerebro `_runnext` / `bbroker._try_exec_market`, `coo`). Signals only use index -1 and earlier.
  `size=` is passed explicitly to buy().
- Indicator values inside next_open (S2): the SMA lines are NOT yet advanced for the new bar, so `sma[0]` = value at the previous bar's close (t), `sma[-1]` = t-1.
  Verified numerically against a manual mean. Using [-1]/[-2] (the naive choice) shifted every entry one day late (first run: 0 matches).
- S1 range, entry/exit window, 78-bar-day filter: valid days precomputed with pandas (count>=78), range high/low accumulated in next_open from bars 09:30-09:55.

## Problems hit
1. S2 entries one day late: indicator indexing in next_open (above). Fixed with [0]/[-1].
2. S2 entry/exit prices equal to the bar CLOSE instead of open: `broker.set_coc(True)` (needed for end-of-window close) applies to every market
   order (`bbroker._try_exec_market`: `if self.p.coc and order.info.get('coc', True)` -> price = order.created.pclose). Fixed by passing `coc=False`
   to the orders that must fill at the open (order.info opt-out) and `coc=True` only for the final close.
3. S2 end-of-window close missing (21 trades dropped): an order created in `next()` on the last bar is never processed, because `_runnext` calls
   `_brokernotify` (broker.next) before `strat._next`, and no further bar exists. Fix: on the last bar (`len(d)==d.buflen()`) place the closing order
   inside `next_open` with `coc=True`; it executes in the same bar's broker pass at `order.created.pclose` = that bar's close. If a buy is also
   signalled on the last bar's open, an explicit `sell(size=n, coc=True)` is placed in the same call (a close() would see position 0).
   This is the engine's cheat-on-close; the decision "hold until the end" does not depend on the close value.
4. S1 22 exit-time mismatches (15:50 vs 15:55): my first reading limited the exit signal to bars <=15:40 together with entries. The protocol
   text for rule 3 states no time window, so the exit signal is evaluated on every bar after the opening range (a 15:45 bar close < range low sells at the 15:50 open);
   only entry is limited to signal bars 10:00-15:40. This is an ambiguity resolution made after seeing compare output (reviewer: confirm it matches intent of STRATEGIES.md).
5. Runtime: S1 takes ~2m45s for 30 symbols (backtrader is slow; no accuracy impact).
- Warm-up (S2): SMA50 needs 50 bars; `next_open` guards `len(d) < 51` (prev bar's SMA50 valid from len 51; t-1 value is nan at len 51 so no signal can fire
  until len 52, comparisons with nan are False). Matches the reference (no mismatches).

## Final compare output
S1: ref_trades 9304, engine_trades 9304, missing 0, extra 0, exit_time/entry_price/exit_price/shares mismatches 0, pnl_mismatch_over_1c 0,
max_abs_pnl_diff 5.0e-07, ref_total_pnl -83953.18, engine_total_pnl -83953.18, PASS true.
S2: ref_trades 179, engine_trades 179, missing 0, extra 0, all mismatches 0, max_abs_pnl_diff 5.0e-07,
ref_total_pnl 54050.15, engine_total_pnl 54050.15, PASS true.
