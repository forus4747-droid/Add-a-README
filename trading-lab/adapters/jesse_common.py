"""Shared helpers for the jesse adapters (S1/S2).

Jesse (3.6.1) research API: jesse.research.backtest(config, routes, data_routes, candles) -- no DB/redis.
Candles are fed as jesse "1m" source rows [ts_ms, open, close, high, low, volume]. Each of OUR bars is
represented by TWO rows (a documented workaround, see reports/notes/jesse.md):
  row A  at bar open time T      : flat opening print   o=h=l=c=bar.open, volume 0
  row B  at T + 1 minute         : o=bar.open, c=bar.close, h=bar.high, l=bar.low, volume=bar.volume
Jesse's own aggregation of A+B into a 5m / 1D bucket gives exactly the original bar (OHLCV).
No rows are invented for the overnight/weekend gaps (jesse 3.6.1 replays sparse observed rows by timestamp).
The strategy acts only on row-A events: its market order is filled by jesse's broker at the current price,
which at that moment is the opening print = the bar's open (= "next bar's open" after the previous bar closed).
"""
import sys, os, math
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd

EXCHANGE = "Alpaca"
SYMBOL_FMT = "{}-USD"      # jesse wants BASE-QUOTE symbols; quote is irrelevant for the futures model
FEE = 0.0005
BALANCE = 1e9


def bars_to_rows(ts_ms, o, h, l, c, v):
    """ts_ms etc: 1-D arrays, one entry per real bar -> (2N,6) jesse candle array [ts,open,close,high,low,vol]."""
    n = len(ts_ms)
    out = np.empty((2 * n, 6), dtype=float)
    out[0::2, 0] = ts_ms;            out[0::2, 1:5] = np.asarray(o)[:, None]; out[0::2, 5] = 0.0
    out[1::2, 0] = np.asarray(ts_ms) + 60_000
    out[1::2, 1] = o; out[1::2, 2] = c; out[1::2, 3] = h; out[1::2, 4] = l; out[1::2, 5] = v
    return out


def run_jesse(sym, strategy_cls, rows, timeframe):
    from jesse.research import backtest
    s = SYMBOL_FMT.format(sym)
    config = {"starting_balance": BALANCE, "fee": FEE, "type": "futures", "futures_leverage": 1,
              "futures_leverage_mode": "cross", "exchange": EXCHANGE, "warm_up_candles": 0}
    routes = [{"exchange": EXCHANGE, "strategy": strategy_cls, "symbol": s, "timeframe": "1m"}]
    data_routes = [{"exchange": EXCHANGE, "symbol": s, "timeframe": timeframe}]
    candles = {f"{EXCHANGE}-{s}": {"exchange": EXCHANGE, "symbol": s, "candles": rows}}
    return backtest(config, routes, data_routes, candles)
