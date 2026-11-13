"""Shared helpers for the freqtrade S1/S2 adapters (run with the freqtrade env python, cwd = trading-lab/).

Everything freqtrade needs is created in a temp user_data dir under /tmp. Nothing is written into the repo
except results/trades/freqtrade_*.csv.
"""
import asyncio, json, logging, os, shutil, sys, tempfile
import pandas as pd

FEE = 0.0005
STAKE = 10000
EXCHANGE = "binance"      # any ccxt exchange would do; only used as a container for fake offline markets
QUOTE = "USD"


def pair_of(sym):
    return f"{sym}/{QUOTE}"


# ----------------------------------------------------------------------------------------------------------
# Offline markets. freqtrade's Exchange.__init__ -> reload_markets -> ccxt load_markets -> fetch_markets (HTTP
# GET https://api.binance.com/api/v3/exchangeInfo). There is no config switch to skip it (freqtrade/exchange/
# exchange.py: Exchange.__init__(validate=True) -> reload_markets(True); validate_stakecurrency raises
# "Could not load markets, therefore cannot start" when markets are empty). Minimal workaround: replace ONLY the
# ccxt method that does the HTTP call (fetch_markets / fetch_currencies of the async ccxt class) with a function
# returning our 30 stock "markets". ccxt's own load_markets()/set_markets() and all of freqtrade run unmodified.
# ----------------------------------------------------------------------------------------------------------
def install_offline_markets(symbols):
    import ccxt.async_support as ccxt_async
    cls = getattr(ccxt_async, EXCHANGE)

    def mk(sym):
        return {
            "id": f"{sym}{QUOTE}", "symbol": pair_of(sym), "base": sym, "quote": QUOTE,
            "baseId": sym, "quoteId": QUOTE, "settle": None, "settleId": None,
            "type": "spot", "spot": True, "margin": False, "swap": False, "future": False, "option": False,
            "contract": False, "linear": None, "inverse": None, "contractSize": None, "active": True,
            "taker": FEE, "maker": FEE, "percentage": True, "tierBased": False,
            # TICK_SIZE precision mode: amount tick 1 => whole shares only; price tick 1e-8 => data never rounded
            "precision": {"amount": 1.0, "price": 1e-8},
            "limits": {"leverage": {"min": None, "max": None}, "amount": {"min": 1.0, "max": None},
                       "price": {"min": None, "max": None}, "cost": {"min": None, "max": None}},
            "created": None, "info": {},
        }
    markets = [mk(s) for s in symbols]

    async def fetch_markets(self, params={}):
        return markets

    async def fetch_currencies(self, params={}):
        return {}
    cls.fetch_markets = fetch_markets
    cls.fetch_currencies = fetch_currencies


def write_data(user_data, frames, timeframe):
    """frames: {sym: DataFrame[date(UTC tz-aware), open, high, low, close, volume]} -> feather files."""
    from freqtrade.data.history import get_datahandler
    from freqtrade.enums import CandleType
    datadir = os.path.join(user_data, "data", EXCHANGE)
    os.makedirs(datadir, exist_ok=True)
    dh = get_datahandler(__import__("pathlib").Path(datadir), "feather")
    for sym, df in frames.items():
        dh.ohlcv_store(pair_of(sym), timeframe, df.reset_index(drop=True), CandleType.SPOT)
    return datadir


def run(tmp, strategy_name, strategy_src, symbols, frames, timeframe):
    """Write data+strategy+config under tmp, run freqtrade Backtesting (Python API), return trades DataFrame."""
    user_data = os.path.join(tmp, "user_data")
    os.makedirs(os.path.join(user_data, "strategies"), exist_ok=True)
    datadir = write_data(user_data, frames, timeframe)
    open(os.path.join(user_data, "strategies", f"{strategy_name}.py"), "w").write(strategy_src)
    cfg = {
        "dry_run": True, "trading_mode": "spot", "stake_currency": QUOTE, "stake_amount": STAKE,
        "dry_run_wallet": 1e12, "max_open_trades": -1, "timeframe": timeframe, "fee": FEE,
        "exchange": {"name": EXCHANGE, "key": "", "secret": "", "pair_whitelist": [pair_of(s) for s in symbols],
                     "pair_blacklist": []},
        "pairlists": [{"method": "StaticPairList"}],
        "entry_pricing": {"price_side": "same", "use_order_book": False},
        "exit_pricing": {"price_side": "same", "use_order_book": False},
        "user_data_dir": user_data, "datadir": datadir, "dataformat_ohlcv": "feather",
        "export": "none", "cache": "none", "backtest_cache": "none",
    }
    cfgpath = os.path.join(tmp, "config.json")
    json.dump(cfg, open(cfgpath, "w"), indent=1)

    install_offline_markets(symbols)
    from freqtrade.configuration import Configuration
    from freqtrade.enums import RunMode
    from freqtrade.optimize.backtesting import Backtesting
    args = {"config": [cfgpath], "user_data_dir": user_data, "datadir": datadir, "strategy": strategy_name,
            "strategy_path": os.path.join(user_data, "strategies"), "export": "none", "cache": "none"}
    config = Configuration(args, RunMode.BACKTEST).get_config()
    bt = Backtesting(config)
    data, timerange = bt.load_bt_data()
    bt.backtest_one_strategy(bt.strategylist[0], data, timerange)
    res = bt.all_bt_content[bt.strategylist[0].get_strategy_name()]
    trades = res["results"].copy()
    trades.attrs["rejected"] = bt.rejected_trades
    return trades


def new_tmp(prefix):
    return tempfile.mkdtemp(prefix=prefix, dir="/tmp")
