"""S2 20/50 SMA cross on jesse (research API). Daily bars from lab.data.daily_from_5min, represented as 2 rows each
inside the UTC day of the session date (see adapters/jesse_common.py). Route '1m' acts on opening-print rows; the '1D'
data route (jesse's own aggregation) supplies the completed daily bars; SMA via jesse.indicators.sma."""
import sys, os, math
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from jesse.strategies import Strategy
import jesse.indicators as ta
from adapters.jesse_common import *
from lab.data import daily_from_5min, DOW

DAY = 86_400_000


class S2(Strategy):
    def _bar_ok(self):
        c = self.current_candle
        if c[0] % DAY != 0:            # row A is stamped at 00:00 UTC of the session date; row B at 00:01 is ignored
            return False
        k = self.get_candles(EXCHANGE, self.symbol, "1D")
        return len(k) >= 52            # k[-1] is the forming day; completed days are k[:-1]; need 50 + 1 for t-1 SMA

    def _cross(self):
        k = self.get_candles(EXCHANGE, self.symbol, "1D")[:-1]          # completed daily bars only
        s20 = ta.sma(k, 20, sequential=True); s50 = ta.sma(k, 50, sequential=True)
        return s20[-1], s50[-1], s20[-2], s50[-2]

    def should_long(self):
        if not self._bar_ok() or self.position.is_open:
            return False
        a, b, pa, pb = self._cross()
        return a > b and pa <= pb

    def go_long(self):
        self.buy = math.floor(10000 / self.price), self.price     # self.price == opening print of day t+1

    def update_position(self):
        if not self._bar_ok():
            return
        a, b, _, _ = self._cross()
        if a < b:
            self.liquidate()

    def should_cancel_entry(self): return False
    def should_short(self): return False
    def go_short(self): pass


def run_symbol(sym):
    d = daily_from_5min(sym)
    ts = (pd.to_datetime(d.date, utc=True).astype("int64") // 10**6).values     # 00:00 UTC of the session date
    rows = bars_to_rows(ts, d.open.values, d.high.values, d.low.values, d.close.values, d.volume.values)
    return run_jesse(sym, S2, rows, "1D")


def to_rows(sym, trades):
    def day(ms):
        return pd.Timestamp(int(ms) - 60_000, unit="ms", tz="UTC").strftime("%Y-%m-%d")
    return [dict(symbol=sym, entry_time=day(t["opened_at"]), entry_price=t["entry_price"], exit_time=day(t["closed_at"]),
                 exit_price=t["exit_price"], shares=int(t["qty"]), pnl_net=t["PNL"]) for t in trades]


if __name__ == "__main__":
    syms = sys.argv[1:] or DOW
    allrows = []
    for s in syms:
        res = run_symbol(s)
        trades = res.get("trades", [])
        print(s, "trades", len(trades), flush=True)
        allrows += to_rows(s, trades)
    cols = ["symbol", "entry_time", "entry_price", "exit_time", "exit_price", "shares", "pnl_net"]
    os.makedirs("results/trades", exist_ok=True)
    out = "results/trades/jesse_S2.csv" if not sys.argv[1:] else "results/trades/jesse_S2_partial.csv"
    pd.DataFrame(allrows, columns=cols).to_csv(out, index=False)
