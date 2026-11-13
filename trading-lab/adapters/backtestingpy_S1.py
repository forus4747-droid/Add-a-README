"""S1 (opening-range breakout) on backtesting.py. Run from trading-lab/: PY adapters/backtestingpy_S1.py"""
import sys, os, warnings
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from backtesting import Backtest, Strategy
from lab.data import load_5min, DOW

FEE = 0.0005
NOTIONAL = 10000.0
CASH = 1e9  # large so the engine never rejects for cash; sizing is made independent of equity below

def commission(order_size, price):
    # Engine calls this with the *fractional* order size while sizing a proportional order
    # (backtesting.py _process_orders: adjusted_price_plus_commission); return 0 there so the
    # engine sizes as floor(budget/price). Real fills (integer size) are charged 0.05% per side.
    if abs(order_size) < 1:
        return 0.0
    return abs(order_size) * price * FEE

class S1(Strategy):
    def init(self):
        self.traded_day = None
    def next(self):
        d = self.data
        if not d.Valid[-1]:
            return
        hm = d.HM[-1]
        day = d.Day[-1]
        if not self.position:
            if 600 <= hm <= 940 and self.traded_day != day and d.Close[-1] > d.RHi[-1]:  # entries 10:00..15:40 bars
                # proportional size in (0,1): the engine computes int(margin_available*size // fill_price) at fill time.
                # equity == cash while flat, so size = 10000/equity gives a 10000 budget (+1e-12 guards float rounding).
                self.buy(size=(NOTIONAL / self.equity) * (1 + 1e-12))
                self.traded_day = day
        else:
            # rule 3 read literally: exit signal on any bar while long (rule 4 forces the 15:50 bar -> 15:55 open)
            if d.Close[-1] < d.RLo[-1] or hm == 950:
                self.position.close()

def prep(sym):
    m = load_5min(sym)
    m = m.sort_values("time_new_york").reset_index(drop=True)
    g = m.groupby("day")
    m["n"] = g.open.transform("size")
    m["k"] = g.cumcount()
    first6 = m[m.k < 6].groupby("day")
    rh = first6.high.max(); rl = first6.low.min()
    m["RHi"] = m.day.map(rh); m["RLo"] = m.day.map(rl)
    m["Valid"] = ((m.n >= 78) & (m.k >= 6)).astype(float)
    m["HM"] = m.hm.str[:2].astype(int) * 60 + m.hm.str[3:].astype(int)  # minutes since midnight: 10:00=600, 15:40=940, 15:50=950
    return m

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    rows = []
    for sym in DOW:
        m = prep(sym)
        m["Day"] = pd.factorize(m.day)[0].astype(float)
        df = m[["open", "high", "low", "close", "volume", "RHi", "RLo", "Valid", "HM", "Day"]].copy()
        df.columns = ["Open", "High", "Low", "Close", "Volume", "RHi", "RLo", "Valid", "HM", "Day"]
        df.index = pd.to_datetime(m.time_new_york.values)
        assert df.index.is_unique and df.index.is_monotonic_increasing
        bt = Backtest(df, S1, cash=CASH, commission=commission, trade_on_close=False,
                      hedging=False, exclusive_orders=False, finalize_trades=False)
        st = bt.run()
        t = st._trades
        for _, r in t.iterrows():
            rows.append((sym, r.EntryTime.strftime("%Y-%m-%d %H:%M"), r.EntryPrice, r.ExitTime.strftime("%Y-%m-%d %H:%M"),
                         r.ExitPrice, int(abs(r.Size)), float(r.PnL)))
        print(sym, len(t), flush=True)
    out = pd.DataFrame(rows, columns="symbol,entry_time,entry_price,exit_time,exit_price,shares,pnl_net".split(","))
    os.makedirs("results/trades", exist_ok=True)
    out.to_csv("results/trades/backtestingpy_S1.csv", index=False)
    print(len(out), out.pnl_net.sum())
