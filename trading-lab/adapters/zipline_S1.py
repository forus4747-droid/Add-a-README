"""S1 (5-min opening-range breakout) on zipline-reloaded MINUTE mode. Run from trading-lab/: PY adapters/zipline_S1.py
zipline's minute store is hard-wired to 1-minute bars (BcolzMinuteBarWriter: one slot per calendar minute, 390/day).
Device: each 5-min bar (O,H,L,C,V intact) is written into the ONE 1-minute slot labelled start+1min (zipline's XNYS minutes are labelled by minute end: first minute is 09:31);
the other four minutes of the bar carry no data (volume 0). Zipline's fill loop skips bars with volume 0, so an order
placed when bar k is visible is filled at the next minute that has data = bar k+1's start, using that bar's open."""
import sys, os, math, tempfile, warnings
sys.path.insert(0, os.getcwd())
warnings.filterwarnings("ignore")
TMP = tempfile.mkdtemp(prefix="zl_S1_", dir="/tmp")
os.environ["ZIPLINE_ROOT"] = TMP
import numpy as np, pandas as pd
from zipline.utils.calendar_utils import get_calendar
from exchange_calendars import register_calendar_type
from exchange_calendars.exchange_calendar_xnys import XNYSExchangeCalendar
from zipline.data import bundles
from zipline.api import order, symbol, set_slippage, set_commission, get_open_orders, cancel_order, set_cancel_policy
from zipline.finance import commission, slippage, cancel_policy
from zipline.utils.run_algo import run_algorithm
from lab.data import load_5min, daily_from_5min, DOW

BUDGET, FEE = 10000.0, 0.0005
class XNYSFullDays(XNYSExchangeCalendar):
    """XNYS without the 13:00 early closes. Needed because the lab's 5-min data has full 78-bar days (to 15:55) on the
    NYSE early-close days; zipline's bar store silently drops minutes outside the calendar session."""
    name = "XNYS_FULLDAYS"
    @property
    def special_closes(self): return []
    @property
    def special_closes_adhoc(self): return []
register_calendar_type("XNYS_FULLDAYS", XNYSFullDays, force=True)
CAL = get_calendar("XNYS_FULLDAYS")
NY = "America/New_York"

MIN, DAILY, VALID = {}, {}, {}
for s in DOW:
    m = load_5min(s)
    ts = pd.to_datetime(m.time_utc.str.replace("Z", ""))              # UTC, naive
    df = m[["open", "high", "low", "close", "volume"]].astype(float).copy(); df.index = ts.values
    df.index = pd.DatetimeIndex(df.index).tz_localize("UTC") + pd.Timedelta(minutes=1)   # XNYS minutes are labelled by minute END (first = 09:31): bar slot = start+1min
    MIN[s] = df
    d = daily_from_5min(s).sort_values("date"); d.index = pd.to_datetime(d.date.values)
    DAILY[s] = d[["open", "high", "low", "close", "volume"]].astype(float)
    VALID[s] = set(m.groupby("day").size().loc[lambda x: x >= 78].index)
START = min(d.index[0] for d in DAILY.values()); END = max(d.index[-1] for d in DAILY.values())

def ingest(environ, asset_db_writer, minute_bar_writer, daily_bar_writer, adjustment_writer, calendar,
           start_session, end_session, cache, show_progress, output_dir):
    meta = pd.DataFrame({"symbol": DOW, "start_date": [DAILY[s].index[0] for s in DOW],
                         "end_date": [DAILY[s].index[-1] for s in DOW],
                         "auto_close_date": [DAILY[s].index[-1] + pd.Timedelta(days=1) for s in DOW], "exchange": "NYSE"})
    asset_db_writer.write(equities=meta)
    # bundles.core builds the minute writer with the default price ratio 1000 (prices stored as uint32 round(p*1000):
    # our 4-decimal prices get rounded to 3). BcolzMinuteBarWriter itself accepts default_ohlc_ratio; use 10000.
    from zipline.data.bcolz_minute_bars import BcolzMinuteBarWriter
    minute_bar_writer = BcolzMinuteBarWriter(minute_bar_writer._rootdir, calendar, start_session, end_session,
                                             minutes_per_day=390, default_ohlc_ratio=10000)
    minute_bar_writer.write(((i, MIN[s]) for i, s in enumerate(DOW)), show_progress=False)
    daily_bar_writer.write(((i, DAILY[s]) for i, s in enumerate(DOW)), show_progress=False)
    adjustment_writer.write()

bundles.register("labmin", ingest, calendar_name="XNYS_FULLDAYS", start_session=START, end_session=END, minutes_per_day=390)

class OpenFillFixedBudget(slippage.EquitySlippageModel):
    """Fills at the current bar's OPEN (built-ins use 'close'); buys sized at fill time floor(BUDGET/open)."""
    def process_order(self, data, order_):
        px = data.current(order_.asset, "open")
        if order_.open_amount > 0:
            n = min(int(math.floor(BUDGET / px)), order_.open_amount)
            return (px, n) if n >= 1 else (None, None)
        return px, order_.open_amount

def initialize(ctx):
    ctx.assets = [symbol(s) for s in DOW]
    ctx.nm = dict(zip(ctx.assets, DOW))
    ctx.day = None
    ctx.st = {}
    set_slippage(us_equities=OpenFillFixedBudget())
    set_commission(us_equities=commission.PerDollar(cost=FEE))
    set_cancel_policy(cancel_policy.NeverCancel())

def handle_data(ctx, data):
    t = (data.current_dt.tz_convert(NY) if data.current_dt.tzinfo else data.current_dt.tz_localize("UTC").tz_convert(NY)) - pd.Timedelta(minutes=1)
    if t.minute % 5:
        return
    hm = t.strftime("%H:%M"); day = t.strftime("%Y-%m-%d")
    if day != ctx.day:
        ctx.day = day; ctx.st = {a: dict(hi=-np.inf, lo=np.inf, traded=False) for a in ctx.assets}
    for a, oo in get_open_orders().items():      # drop unfilled remainder of the oversized buy orders
        for o in oo:
            if o.amount > 0: cancel_order(o)
    vol = data.current(ctx.assets, "volume")
    hi_, lo_, cl_ = (data.current(ctx.assets, f) for f in ("high", "low", "close"))
    for a in ctx.assets:
        if vol[a] <= 0 or day not in VALID[ctx.nm[a]]:
            continue
        st = ctx.st[a]
        if hm <= "09:55":
            st["hi"] = max(st["hi"], hi_[a]); st["lo"] = min(st["lo"], lo_[a]); continue
        pos = ctx.portfolio.positions.get(a); held = pos.amount if pos is not None else 0
        pend = get_open_orders(a)
        if held == 0 and not pend:
            if not st["traded"] and "10:00" <= hm <= "15:40" and cl_[a] > st["hi"]:
                order(a, 10**9); st["traded"] = True
        elif held > 0 and not pend:
            if hm == "15:50" or (hm <= "15:45" and cl_[a] < st["lo"]):
                order(a, -held)

if __name__ == "__main__":
    bundles.ingest("labmin", os.environ, pd.Timestamp.utcnow(), [], show_progress=False)
    res = run_algorithm(start=START, end=END, initialize=initialize, handle_data=handle_data, capital_base=1e9,
                        data_frequency="minute", bundle="labmin", trading_calendar=CAL,
                        benchmark_returns=pd.Series(0.0, index=CAL.sessions_in_range(START, END)))
    tx = []
    for dt, row in res.transactions.items():
        for t in row:
            ts = pd.Timestamp(t["dt"]); ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts
            tx.append((ts.tz_convert(NY) - pd.Timedelta(minutes=1), t["sid"].symbol, t["amount"], t["price"]))
    tx = pd.DataFrame(tx, columns=["ts", "sym", "amt", "px"]).sort_values(["sym", "ts"])
    rows = []
    for sym, g in tx.groupby("sym"):
        g = g.reset_index(drop=True)
        assert len(g) % 2 == 0 and (g.amt[::2] > 0).all() and (g.amt[1::2] < 0).all(), sym
        for i in range(0, len(g), 2):
            b, s_ = g.iloc[i], g.iloc[i + 1]; assert b.amt == -s_.amt
            pnl = (s_.px - b.px) * b.amt - FEE * b.px * b.amt - FEE * s_.px * b.amt
            rows.append((sym, b.ts.strftime("%Y-%m-%d %H:%M"), b.px, s_.ts.strftime("%Y-%m-%d %H:%M"), s_.px, int(b.amt), pnl))
    out = pd.DataFrame(rows, columns="symbol,entry_time,entry_price,exit_time,exit_price,shares,pnl_net".split(","))
    out.to_csv("results/trades/zipline_S1.csv", index=False)
    print(len(out), out.pnl_net.sum(), "engine portfolio pnl:", float(res.portfolio_value.iloc[-1] - 1e9))
