"""S1 opening-range breakout on jesse (research API, no DB). See adapters/jesse_common.py for the data workaround."""
import sys, os, math
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from jesse.strategies import Strategy
from adapters.jesse_common import *
from lab.data import load_5min, DOW

BAR = 300_000
META = {}   # filled per symbol: bar_ts_ms -> (day_id, minute_of_day_NY); VALID: set of day_ids with >= 78 bars


class S1(Strategy):
    def __init__(self):
        super().__init__()
        self.day = None; self.hi = None; self.lo = None; self.traded = False; self.nbars_range = 0

    # --- everything happens in should_long()/update_position() on the opening-print event (row A) ---
    def _bar(self):
        """Return the just-completed 5m bar (ndarray) if this is an opening-print event, else None."""
        c = self.current_candle
        if c[0] % BAR != 0:
            return None
        k = self.get_candles(EXCHANGE, self.symbol, "5m")
        if len(k) < 2:
            return None
        b = k[-2]                      # k[-1] is the forming bucket (only the opening print so far)
        if b[0] != c[0] - BAR:         # previous bar is not the immediately preceding 5 minutes (day start)
            return None
        return b

    def _classify(self, b):
        day, mod = META[int(b[0])]
        if day != self.day:
            self.day = day; self.hi = -np.inf; self.lo = np.inf; self.traded = False
        return day, mod

    def should_long(self):
        b = self._bar()
        if b is None or self.position.is_open:
            return False
        day, mod = self._classify(b)
        if day not in VALID:
            return False
        if 570 <= mod <= 595:                      # 09:30..09:55 bars -> opening range
            self.hi = max(self.hi, b[3]); self.lo = min(self.lo, b[4])
            return False
        if 600 <= mod <= 940 and not self.traded and b[2] > self.hi:     # 10:00..15:40 bars
            return True
        return False

    def go_long(self):
        qty = math.floor(10000 / self.price)     # self.price == fill price (opening print of the fill bar)
        self.buy = qty, self.price
        self.traded = True

    def update_position(self):
        b = self._bar()
        if b is None:
            return
        day, mod = self._classify(b)
        if (mod <= 945 and b[2] < self.lo) or mod == 950:   # rule 3 (<=15:45 bar close) / rule 4 (15:50 bar -> sell 15:55 open)
            self.liquidate()

    def should_cancel_entry(self): return False
    def should_short(self): return False
    def go_short(self): pass


VALID = set()


def run_symbol(sym):
    global VALID
    m = load_5min(sym)
    t = pd.to_datetime(m.time_utc, utc=True)
    ts = (t.astype("int64") // 10**6).values          # pandas 2.2: ns resolution
    day_codes, day_uniques = pd.factorize(m.day)
    mod = m.hm.str[:2].astype(int).values * 60 + m.hm.str[3:5].astype(int).values
    META.clear(); META.update({int(a): (int(d), int(h)) for a, d, h in zip(ts, day_codes, mod)})
    cnt = m.groupby("day").size()
    VALID = {int(i) for i, d in enumerate(day_uniques) if cnt[d] >= 78}
    rows = bars_to_rows(ts, m.open.values, m.high.values, m.low.values, m.close.values, m.volume.values)
    res = run_jesse(sym, S1, rows, "5m")
    return res, m


def to_rows(sym, trades):
    """jesse stamps a fill with the END of the 1m row that carries it (row A at T -> T+60s); subtract 60s -> bar open T."""
    def ny(ms):
        return pd.Timestamp(int(ms) - 60_000, unit="ms", tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d %H:%M")
    return [dict(symbol=sym, entry_time=ny(t["opened_at"]), entry_price=t["entry_price"], exit_time=ny(t["closed_at"]),
                 exit_price=t["exit_price"], shares=int(t["qty"]), pnl_net=t["PNL"]) for t in trades]


if __name__ == "__main__":
    syms = sys.argv[1:] or DOW
    allrows = []
    for s in syms:
        res, m = run_symbol(s)
        trades = res.get("trades", [])
        print(s, "trades", len(trades), flush=True)
        allrows += to_rows(s, trades)
    cols = ["symbol", "entry_time", "entry_price", "exit_time", "exit_price", "shares", "pnl_net"]
    os.makedirs("results/trades", exist_ok=True)
    out = "results/trades/jesse_S1.csv" if not sys.argv[1:] else "results/trades/jesse_S1_partial.csv"
    pd.DataFrame(allrows, columns=cols).to_csv(out, index=False)
