import sys, os
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd, vectorbt as vbt
from lab.data import daily_from_5min, DOW
FEE = 0.0005
out = []
for sym in DOW:
    d = daily_from_5min(sym).reset_index(drop=True)
    s20 = d.close.rolling(20).mean(); s50 = d.close.rolling(50).mean()
    cross_up = ((s20 > s50) & (s20.shift(1) <= s50.shift(1))).fillna(False).values
    below = (s20 < s50).fillna(False).values
    entries = pd.Series(cross_up).shift(1, fill_value=False).values   # decided at close t, fill at open t+1
    exits = pd.Series(below).shift(1, fill_value=False).values
    # protocol: open position at window end is closed at last day's close -> sentinel bar whose "open" = last close
    last_date = d.date.iloc[-1]
    dates = pd.DatetimeIndex(list(d.date) + [pd.Timestamp(last_date) + pd.Timedelta(days=1)])
    price = pd.Series(list(d.open.values) + [d.close.iloc[-1]], index=dates)
    entries = pd.Series(list(entries) + [False], index=dates)
    exits = pd.Series(list(exits) + [True], index=dates)
    size = np.floor(10000 / price)
    pf = vbt.Portfolio.from_signals(price, entries=entries, exits=exits, price=price, size=size,
        size_type="amount", fees=FEE, init_cash=1e9, direction="longonly", accumulate=False, freq="1D")
    for _, r in pf.trades.records_readable.iterrows():
        assert r["Status"] == "Closed", (sym, r)
        ex = r["Exit Timestamp"]
        ex = last_date if ex == dates[-1] else ex.strftime("%Y-%m-%d")
        out.append(dict(symbol=sym, entry_time=r["Entry Timestamp"].strftime("%Y-%m-%d"), entry_price=r["Avg Entry Price"],
            exit_time=ex, exit_price=r["Avg Exit Price"], shares=int(round(r["Size"])), pnl_net=r["PnL"]))
os.makedirs("results/trades", exist_ok=True)
pd.DataFrame(out).to_csv("results/trades/vectorbt_S2.csv", index=False)
print(len(out), "trades")
