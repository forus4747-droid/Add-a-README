"""Shared nautilus_trader harness (BacktestEngine, low-level API) for S1/S2.
Design: the venue is driven ONLY by QuoteTicks (bid=ask=bar open) so market orders fill at the bar open.
Bars (ts_init = bar CLOSE time) are given to the strategy for signals; they are not given to the venue
(bar_execution=False). The 'open' quote of bar N+1 is stamped close(N)+1ns so the strategy always sees bar N
first. On that quote the strategy submits the market order -> fills at the quote (=open) -> size known."""
import sys, os, math
sys.path.insert(0, os.getcwd())
from decimal import Decimal
import pandas as pd
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.data import Bar, BarType, BarSpecification, QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide, BarAggregation, PriceType, AggregationSource
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.config import StrategyConfig

VENUE = Venue("SIM")
FEE = Decimal("0.0005")
NS5 = 300 * 10**9
PREC = 6   # data has sub-cent prices (e.g. 187.845, 175.4579); 2dp would round them

def make_instrument(sym):
    return Equity(instrument_id=InstrumentId(Symbol(sym), VENUE), raw_symbol=Symbol(sym), currency=USD,
                  price_precision=PREC, price_increment=Price.from_str("0." + "0"*(PREC-1) + "1"), lot_size=Quantity.from_int(1),
                  maker_fee=FEE, taker_fee=FEE, ts_event=0, ts_init=0)

def make_engine(inst):
    eng = BacktestEngine(BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR", bypass_logging=True)))
    eng.add_venue(venue=VENUE, oms_type=OmsType.NETTING, account_type=AccountType.CASH, base_currency=USD,
                  starting_balances=[Money(10_000_000, USD)], bar_execution=False, trade_execution=False,
                  support_gtd_orders=False)
    eng.add_instrument(inst)
    return eng

def quote(inst, price, ts):
    p = Price(price, PREC); q = Quantity.from_int(1_000_000)
    return QuoteTick(inst.id, p, p, q, q, ts, ts)

def bar(inst, bt, o, h, l, c, v, ts):
    return Bar(bt, Price(o, PREC), Price(h, PREC), Price(l, PREC), Price(c, PREC), Quantity(max(int(v), 1), 0), ts, ts)

def utc_ns(s):
    return pd.to_datetime(s, utc=True).astype("int64") if hasattr(pd.to_datetime(s, utc=True), "astype") else None

class Base(Strategy):
    def __init__(self, inst, bt, meta, final_ts=None):
        super().__init__(StrategyConfig(strategy_id=f"{type(self).__name__}-001", order_id_tag="001"))
        self.inst, self.bt, self.meta, self.final_ts = inst, bt, meta, final_ts
        self.pending = None

    def on_start(self):
        self.subscribe_bars(self.bt)
        self.subscribe_quote_ticks(self.inst.id)

    def flat(self):
        return self.portfolio.is_flat(self.inst.id)

    def order(self, side, qty):
        self.submit_order(self.order_factory.market(self.inst.id, side, Quantity.from_int(qty)))

def run_symbol(strat_cls, sym, bars_list, quotes_list, meta, bt, final_ts=None):
    """returns list of trades: dict(entry_ts, entry_price, exit_ts, exit_price, shares, pnl_net)"""
    inst = make_instrument(sym)
    eng = make_engine(inst)
    data = sorted(bars_list + quotes_list, key=lambda d: d.ts_init)  # stable: bars before quotes at equal ts
    eng.add_data(data)
    st = strat_cls(inst, bt, meta, final_ts)
    eng.add_strategy(st)
    eng.run()
    trades = []
    rep = eng.trader.generate_positions_report()
    fills = eng.trader.generate_order_fills_report()
    pos = rep.reset_index()
    if os.environ.get("NDBG"): print(pos.head(3).T); print(fills.head(4).T)
    fills = fills.reset_index()
    out = []
    for _, r in pos.sort_values("ts_opened").iterrows():
        pnl = float(str(r["realized_pnl"]).split()[0])
        out.append(dict(entry_ts=pd.Timestamp(r["ts_opened"]).value,
                        exit_ts=pd.Timestamp(r["ts_closed"]).value,
                        entry_price=float(r["avg_px_open"]), exit_price=float(r["avg_px_close"]),
                        shares=int(float(r["peak_qty"])), pnl_net=pnl))
    eng.dispose()
    return out
