"""S2 (20/50-day SMA cross, daily bars built from 5-min) on freqtrade. Run from trading-lab/ with the freqtrade env python.
Default: trading-day-indexed synthetic calendar (no calendar gaps => freqtrade's gap filling never fabricates rows).
`--naive`: real calendar dates (weekend/holiday gaps get filled by freqtrade) -> writes results/trades/freqtradenaive_S2.csv
for the documented comparison only.
"""
import sys, os, shutil
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "adapters"))
import pandas as pd
from lab.data import daily_from_5min, DOW
import freqtrade_common as fc

NAIVE = "--naive" in sys.argv

STRATEGY = '''
import pandas as pd
from freqtrade.strategy import IStrategy

class S2Strategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1d"
    can_short = False
    minimal_roi = {"0": 1000}
    stoploss = -0.99
    use_exit_signal = True
    exit_profit_only = False
    startup_candle_count = 0

    def populate_indicators(self, df, metadata):
        df["sma20"] = df["close"].rolling(20).mean()
        df["sma50"] = df["close"].rolling(50).mean()
        n = len(df)
        df["last_real"] = False          # last real trading day (the row before the sentinel)
        df.loc[df.index[n - 2], "last_real"] = True
        df["sentinel"] = False           # extra final row: open = last real day's close (see notes: end-of-window rule)
        df.loc[df.index[n - 1], "sentinel"] = True
        return df

    def populate_entry_trend(self, df, metadata):
        cross = (df["sma20"] > df["sma50"]) & (df["sma20"].shift(1) <= df["sma50"].shift(1))
        df["enter_long"] = (cross & ~df["last_real"] & ~df["sentinel"]).astype(int)
        return df

    def populate_exit_trend(self, df, metadata):
        # rule 3 + rule 4: still long after the last real day -> exit signal on last real day, filled at the
        # sentinel row's open (= last day's close)
        df["exit_long"] = ((df["sma20"] < df["sma50"]) | df["last_real"]).astype(int)
        return df
'''

base = pd.Timestamp("2000-01-03", tz="UTC")
frames, back = {}, {}
for sym in DOW:
    d = daily_from_5min(sym)
    real = pd.to_datetime(d.date).dt.tz_localize("UTC")
    n = len(d)
    if NAIVE:
        dates = list(real) + [real.iloc[-1] + pd.Timedelta(days=1)]
    else:
        dates = [base + pd.Timedelta(days=k) for k in range(n + 1)]
    last = d.iloc[-1]
    row = pd.DataFrame({"open": [last.close], "high": [last.close], "low": [last.close], "close": [last.close], "volume": [0.0]})
    body = d[["open", "high", "low", "close", "volume"]].astype(float)
    f = pd.concat([body, row], ignore_index=True)
    f.insert(0, "date", pd.to_datetime(dates, utc=True))
    frames[sym] = f
    back[sym] = {dt: (d.date.iloc[min(k, n - 1)]) for k, dt in enumerate(f.date)}   # sentinel -> last real day

tmp = fc.new_tmp("ft_S2_")
trades = fc.run(tmp, "S2Strategy", STRATEGY, DOW, frames, "1d")
print("rejected:", trades.attrs["rejected"], "exit reasons:", trades.exit_reason.value_counts().to_dict())
sym = trades.pair.str.split("/").str[0]
real_date = lambda col: [back[s].get(pd.Timestamp(t), pd.Timestamp(t).strftime("%Y-%m-%d")) for s, t in zip(sym, trades[col])]
out = pd.DataFrame({"symbol": sym, "entry_time": real_date("open_date"), "entry_price": trades.open_rate,
                    "exit_time": real_date("close_date"), "exit_price": trades.close_rate,
                    "shares": trades.amount.round().astype(int), "pnl_net": trades.profit_abs}
                   ).sort_values(["symbol", "entry_time"])
os.makedirs("results/trades", exist_ok=True)
out.to_csv("results/trades/freqtradenaive_S2.csv" if NAIVE else "results/trades/freqtrade_S2.csv", index=False)
print(len(out), "trades"); shutil.rmtree(tmp, ignore_errors=True)
