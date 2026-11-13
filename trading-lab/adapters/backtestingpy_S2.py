"""S2 (20/50 SMA cross, daily bars) on backtesting.py. Run from trading-lab/: PY adapters/backtestingpy_S2.py"""
import sys, os, warnings
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from backtesting import Backtest, Strategy
from lab.data import daily_from_5min, DOW

FEE = 0.0005
NOTIONAL = 10000.0
CASH = 1e9

def commission(order_size, price):
    # 0 while the engine sizes a proportional (<1) order, so it sizes floor(budget/fill_price); real fills pay 0.05%/side
    if abs(order_size) < 1:
        return 0.0
    return abs(order_size) * price * FEE

def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()

class S2(Strategy):
    def init(self):
        self.s20 = self.I(sma, self.data.Close, 20)
        self.s50 = self.I(sma, self.data.Close, 50)
    def next(self):
        a, b = self.s20, self.s50
        if len(a) < 2:
            return
        if self.data.Last[-1]:  # last real day: close any open position (fills at the sentinel bar's open == this close)
            if self.position:
                self.position.close()
            return
        if self.data.Last[-1] < 0:
            return  # sentinel bar: nothing to do
        if not self.position:
            if a[-1] > b[-1] and a[-2] <= b[-2]:
                self.buy(size=(NOTIONAL / self.equity) * (1 + 1e-12))
        elif a[-1] < b[-1]:
            self.position.close()

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    rows = []
    for sym in DOW:
        d = daily_from_5min(sym).sort_values("date").reset_index(drop=True)
        df = d[["open", "high", "low", "close", "volume"]].copy()
        df.columns = ["Open", "High", "Low", "Close", "Volume"]
        df["Last"] = 0.0
        df.iloc[-1, df.columns.get_loc("Last")] = 1.0
        df.index = pd.to_datetime(d.date.values)
        # Sentinel bar: engine fills market orders at the NEXT bar's open and (finalize_trades) at the last bar's
        # OPEN, never at a close. To realise "close at last day's close" with engine fills, append one bar whose
        # open == last close; exit time is mapped back to the last real date below.
        last_date = df.index[-1]
        df.loc[last_date + pd.Timedelta(days=1)] = [df.Close.iloc[-1]] * 4 + [0.0, -1.0]
        bt = Backtest(df, S2, cash=CASH, commission=commission, trade_on_close=False,
                      hedging=False, exclusive_orders=False, finalize_trades=False)
        st = bt.run()
        t = st._trades
        for _, r in t.iterrows():
            rows.append((sym, r.EntryTime.strftime("%Y-%m-%d"), r.EntryPrice, min(r.ExitTime, last_date).strftime("%Y-%m-%d"),
                         r.ExitPrice, int(abs(r.Size)), float(r.PnL)))
        print(sym, len(t), flush=True)
    out = pd.DataFrame(rows, columns="symbol,entry_time,entry_price,exit_time,exit_price,shares,pnl_net".split(","))
    out.to_csv("results/trades/backtestingpy_S2.csv", index=False)
    print(len(out), out.pnl_net.sum())
