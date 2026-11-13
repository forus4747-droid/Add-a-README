"""Shared helpers for the vnpy (vnpy_ctastrategy BacktestingEngine) adapters.
Bars are fed straight into engine.history_data (no database). All fills come from BacktestingEngine.cross_limit_order."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import math
from datetime import datetime
import pandas as pd
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy_ctastrategy.backtesting import BacktestingEngine
from vnpy_ctastrategy import CtaTemplate

FEE = 0.0005
NOTIONAL = 10000.0
BUY_LIMIT = 1e7      # marketable buy limit: engine fills at min(order.price, bar.open) = bar.open
SELL_LIMIT = 1e-6    # marketable sell limit: engine fills at max(order.price, bar.open) = bar.open
PRICETICK = 1e-6


class SizedTemplate(CtaTemplate):
    """Common order logic. Share count is floor(10000/fill price). The fill price (next bar open) is unknown when
    buy() is called, so the volume is set in on_order(): BacktestingEngine.cross_limit_order calls on_order() with
    status NOTTRADED for each active order on the new bar BEFORE it tests/fills the order, and engine.bar is already
    the new bar, so bar.open_price (the exact future fill price) is known there and legitimately available."""

    def on_order(self, order):
        from vnpy.trader.constant import Direction, Status
        if order.direction == Direction.LONG and order.status == Status.NOTTRADED and order.traded == 0:
            order.volume = math.floor(NOTIONAL / self.cta_engine.bar.open_price)

    def on_trade(self, trade):
        pass

    def send_buy(self):
        self.buy(BUY_LIMIT, 1)       # placeholder volume, replaced in on_order()

    def send_sell(self):
        self.sell(SELL_LIMIT, abs(self.pos))


def make_bars(sym, dts, o, h, l, c, v, interval):
    ex = Exchange.SMART
    return [BarData(symbol=sym, exchange=ex, datetime=d, interval=interval, volume=float(vv), open_price=float(oo),
                    high_price=float(hh), low_price=float(ll), close_price=float(cc), gateway_name="DB")
            for d, oo, hh, ll, cc, vv in zip(dts, o, h, l, c, v)]


def run_engine(sym, bars, interval, strategy_cls, setting, start, end):
    e = BacktestingEngine()
    e.set_parameters(vt_symbol=f"{sym}.SMART", interval=interval, start=start, end=end, rate=FEE, slippage=0.0,
                     size=1, pricetick=PRICETICK, capital=1_000_000)
    e.add_strategy(strategy_cls, setting)
    e.history_data = bars            # bypass the database (load_data not called)
    e.run_backtesting()
    return e


def round_trips(sym, engine, fmt, map_time=lambda t: t):
    """Pair the engine's individual fills (alternating BUY, SELL; one position per symbol) into round trips.
    pnl_net from the engine's fill prices/volumes with the protocol fee (the CTA engine only reports commission
    as a per-day aggregate in DailyResult, not per trade)."""
    from vnpy.trader.constant import Direction
    tr = sorted(engine.get_all_trades(), key=lambda t: (t.datetime, int(t.tradeid)))
    rows, i = [], 0
    while i < len(tr):
        b = tr[i]
        assert b.direction == Direction.LONG, (sym, b)
        if i + 1 >= len(tr):
            raise RuntimeError(f"{sym}: position left open at {b.datetime}")
        s = tr[i + 1]
        assert s.direction == Direction.SHORT and s.volume == b.volume, (sym, b, s)
        n = int(b.volume)
        pnl = (s.price - b.price) * n - FEE * n * (b.price + s.price)
        rows.append((sym, map_time(b.datetime).strftime(fmt), b.price, map_time(s.datetime).strftime(fmt), s.price, n, pnl))
        i += 2
    return rows, engine
