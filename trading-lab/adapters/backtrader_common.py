"""Shared helpers for backtrader adapters. One Cerebro per symbol; cheat-on-open used for sizing on fill-bar open."""
import sys, os, math
sys.path.insert(0, os.getcwd())
import backtrader as bt, pandas as pd

COMM = 0.0005
CASH = 1e9

class Base(bt.Strategy):
    def __init__(self):
        self.rows = []; self._entry = None
    def notify_order(self, order):
        if order.status != order.Completed: return
        dt = bt.num2date(order.executed.dt)
        if order.isbuy():
            self._entry = (dt, order.executed.price, order.executed.size)
        else:
            self._exit = (dt, order.executed.price)
    def notify_trade(self, trade):
        if trade.isclosed:
            e = self._entry; x = self._exit
            self.rows.append(dict(entry_time=e[0], entry_price=e[1], exit_time=x[0],
                                  exit_price=x[1], shares=int(e[2]), pnl_net=trade.pnlcomm))

def run(sym, df, strat, fmt, tf, comp, **kw):
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcash(CASH)
    cerebro.broker.setcommission(commission=COMM)   # percentage, stocklike, per side
    cerebro.broker.set_coc(True) if kw.pop("coc", False) else None
    cerebro.broker.set_checksubmit(False)
    d = df.set_index("dt")[["open", "high", "low", "close", "volume"]]
    feed = bt.feeds.PandasData(dataname=d, timeframe=tf, compression=comp, openinterest=None)
    cerebro.adddata(feed)
    cerebro.addstrategy(strat, **kw)
    s = cerebro.run(cheat_on_open=True)[0]
    out = pd.DataFrame(s.rows); out["symbol"] = sym
    if len(out):
        out["entry_time"] = out.entry_time.dt.strftime(fmt); out["exit_time"] = out.exit_time.dt.strftime(fmt)
    return out
