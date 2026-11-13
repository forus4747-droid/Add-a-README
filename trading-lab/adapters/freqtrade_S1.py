"""S1 (opening-range breakout, 5-min) on freqtrade. Run from trading-lab/ with the freqtrade env python."""
import sys, os, shutil
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "adapters"))
import pandas as pd
from lab.data import load_5min, DOW
import freqtrade_common as fc

STRATEGY = '''
import pandas as pd
from freqtrade.strategy import IStrategy

class S1Strategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    minimal_roi = {"0": 1000}
    stoploss = -0.99
    use_exit_signal = True
    exit_profit_only = False
    startup_candle_count = 0
    process_only_new_candles = True

    def populate_indicators(self, df, metadata):
        # freqtrade candle dates are UTC candle-open times; protocol rules are in New York local time (DST aware)
        ny = df["date"].dt.tz_convert("America/New_York")
        df["day"] = ny.dt.strftime("%Y-%m-%d")
        df["hm"] = ny.dt.strftime("%H:%M")
        # freqtrade fills the overnight/weekend gaps with fake volume-0 candles; count only real bars (volume > 0)
        df["real"] = df["volume"] > 0
        cnt = df["real"].astype(int).groupby(df["day"]).transform("sum")
        df["ok"] = cnt >= 78
        orb = df[df["hm"].between("09:30", "09:55") & df["real"]].groupby("day").agg(rh=("high", "max"), rl=("low", "min"))
        df["rh"] = df["day"].map(orb["rh"])
        df["rl"] = df["day"].map(orb["rl"])
        return df

    def populate_entry_trend(self, df, metadata):
        up = df["hm"].between("10:00", "15:40") & df["ok"] & df["real"] & (df["close"] > df["rh"])
        first = up & (up.astype(int).groupby(df["day"]).cumsum() == 1)   # one trade per day
        df["enter_long"] = first.astype(int)
        return df

    def populate_exit_trend(self, df, metadata):
        stop = df["hm"].between("10:00", "15:50") & df["ok"] & df["real"] & (df["close"] < df["rl"])
        force = (df["hm"] == "15:50") & df["ok"] & df["real"]   # executes at the open of the 15:55 bar
        df["exit_long"] = (stop | force).astype(int)
        return df
'''

frames = {}
for sym in DOW:
    d = load_5min(sym)
    frames[sym] = pd.DataFrame({"date": pd.to_datetime(d.time_utc, utc=True), "open": d.open, "high": d.high,
                                "low": d.low, "close": d.close, "volume": d.volume.astype(float)})
tmp = fc.new_tmp("ft_S1_")
trades = fc.run(tmp, "S1Strategy", STRATEGY, DOW, frames, "5m")
print("rejected:", trades.attrs["rejected"], "exit reasons:", trades.exit_reason.value_counts().to_dict())
ny = lambda s: pd.to_datetime(s, utc=True).dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d %H:%M")
out = pd.DataFrame({"symbol": trades.pair.str.split("/").str[0], "entry_time": ny(trades.open_date),
                    "entry_price": trades.open_rate, "exit_time": ny(trades.close_date),
                    "exit_price": trades.close_rate, "shares": trades.amount.round().astype(int),
                    "pnl_net": trades.profit_abs}).sort_values(["symbol", "entry_time"])
os.makedirs("results/trades", exist_ok=True)
out.to_csv("results/trades/freqtrade_S1.csv", index=False)
print(len(out), "trades"); shutil.rmtree(tmp, ignore_errors=True)
