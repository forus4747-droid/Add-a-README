"""S2 (20/50 SMA cross, daily bars from 5-min) on vnpy_ctastrategy BacktestingEngine. Run from trading-lab/: PY adapters/vnpy_S2.py
Last-day-close exit: the engine only fills limit orders at the NEXT bar's open (cross_limit_order), so one sentinel bar
(date = last date + 1 day, O=H=L=C = last real close, volume 0) is appended; the exit fills at its open (= last close)
and the exit date is mapped back to the last real date."""
import sys, os
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "adapters"))
from datetime import timedelta
from vnpy_common import *
from lab.data import daily_from_5min, DOW


class S2(SizedTemplate):
    last_real = None
    author = "lab"

    def on_init(self):
        self.closes = []; self.prev_diff = None

    def on_bar(self, bar):
        if bar.datetime >= self.last_real + timedelta(days=1):   # sentinel bar: nothing to do
            return
        self.closes.append(bar.close_price)
        c = self.closes
        is_last = bar.datetime == self.last_real
        if len(c) < 50:
            return
        s20 = sum(c[-20:]) / 20; s50 = sum(c[-50:]) / 50
        if len(c) > 50:
            p20 = sum(c[-21:-1]) / 20; p50 = sum(c[-51:-1]) / 50
            prev_le = p20 <= p50
        else:
            prev_le = False          # no SMA20/SMA50 at t-1 yet (needs 50 closes)
        if self.pos == 0:
            if not is_last and s20 > s50 and prev_le:
                self.send_buy()
        else:
            if is_last or s20 < s50:                 # last day: exit order fills at sentinel open = last close
                self.send_sell()


if __name__ == "__main__":
    rows = []
    for sym in DOW:
        d = daily_from_5min(sym).sort_values("date").reset_index(drop=True)
        dts = list(pd.to_datetime(d.date.values).to_pydatetime())
        last = dts[-1]; S2.last_real = last
        bars = make_bars(sym, dts, d.open, d.high, d.low, d.close, d.volume, Interval.DAILY)
        lc = float(d.close.iloc[-1])
        bars += make_bars(sym, [last + timedelta(days=1)], [lc], [lc], [lc], [lc], [0], Interval.DAILY)
        e = run_engine(sym, bars, Interval.DAILY, S2, {}, dts[0], last + timedelta(days=1))
        r, _ = round_trips(sym, e, "%Y-%m-%d", map_time=lambda t: min(t, last))
        rows += r; print(sym, len(r), flush=True)
    out = pd.DataFrame(rows, columns="symbol,entry_time,entry_price,exit_time,exit_price,shares,pnl_net".split(","))
    os.makedirs("results/trades", exist_ok=True)
    out.to_csv("results/trades/vnpy_S2.csv", index=False)
    print(len(out), out.pnl_net.sum())
