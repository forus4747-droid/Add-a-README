# ftsample / ft_minimal (Freqtrade template signal rules)
Source: freqtrade/templates/sample_strategy.py (SampleStrategy) and templates/strategy_subtemplates/*.j2 ("minimal", "full").
Code: skills/ftsample/run.py (build | trunc), skills/ftsample/render_templates.py (renders FtMinimal/FtFull with freqtrade's own deploy_new_strategy).

## Method
- Signals come from each class's own populate_indicators / populate_entry_trend / populate_exit_trend, called on a DataFrame [date,open,high,low,close,volume]. Class instantiated with a minimal config dict {strategy, runmode:'other', timeframe, stake_currency, dry_run}; no engine/exchange/network. Defaults: buy_rsi=30, sell_rsi=70, short_rsi=70 (the `default=` values). No tuning.
- score = +1 enter_long, -1 exit_long or enter_short, 0 if none or both fire. exit_short ignored (can_short=False; it is a cover signal, not a prediction of a fall).
- Indicators computed on the continuous real-bar series: 5m from 2023-08-01 (all bars, no fake overnight candles), daily from 2016. Signals kept for 2024-07-01..2025-12-31 (bar) and 2024-01-01..2025-12-31 (swing). Bar time = NY time of the bar whose close produced the signal.
- Rule sets: ftsample = RSI crosses above 30 AND tema<=BB mid AND tema rising (buy); RSI crosses above 70 AND tema>BB mid AND tema falling (sell). ft_minimal (template "minimal") = RSI cross above 30 (buy) / above 70 (sell), no guards. ft_full (template "full") renders to logic identical to ftsample long/exit (shorts commented out in the template); the parquet outputs were verified equal, so it is not scored separately. FreqAI example strategies need trained ML models: out of scope.
- pyarrow was already installed in the freqtrade env; nothing installed.

## Truncation test (future cut, full past kept)
ftsample: bar GS 2024-09-20 10:05 (+1 vs +1), HON 2025-08-06 10:40 (0/0), AMGN 2024-08-13 15:10 (0/0); swing STZ 2025-01-27 (+1/+1), EXPD 2025-03-12 (0/0), AMD 2025-11-07 (0/0). All equal.
ft_minimal: bar GS 2024-10-04 14:45 (-1/-1), HON, AMGN (0/0); swing STZ 2025-09-29 (+1/+1), AXP 2024-09-30, MGM 2024-02-13 (0/0). All equal. (Sample seeded random; first draw of each mode forced to a firing bar.)
Caveat: RSI/TEMA/HT_SINE have infinite memory; results depend on where the series starts (5m starts 2023-08-01, so warm-up is long finished by 2024-07).

## Firing frequency (2025, 5m: buy / sell per symbol-year; daily per stock-year)
- ftsample 5m: ~174 buys, ~4.5 sells per symbol-year; daily: ~1.9 buys, ~0.05 sells (23 sells in total across 500 stocks in 2025). The sell rule almost never fires; the buy rule fires rarely on daily bars.
- ft_minimal 5m: ~269 buys, ~296 sells; daily: ~3.0 buys, ~4.2 sells.

## Results: see scorer tables in final message; none PREDICTS.
