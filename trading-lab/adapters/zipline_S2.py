"""S2 (20/50 SMA cross, daily bars) on zipline-reloaded. Run from trading-lab/: PY adapters/zipline_S2.py
Custom in-memory bundle written to a temp dir under /tmp (ZIPLINE_ROOT); nothing is written into the repo except the CSV."""
import sys, os, math, tempfile, warnings
sys.path.insert(0, os.getcwd())
warnings.filterwarnings("ignore")
TMP = tempfile.mkdtemp(prefix="zl_S2_", dir="/tmp")
os.environ["ZIPLINE_ROOT"] = TMP
import numpy as np, pandas as pd
from zipline.utils.calendar_utils import get_calendar
from zipline.data import bundles
from zipline.api import (order, symbol, set_slippage, set_commission, set_benchmark, get_open_orders,
                         cancel_order, record, set_cancel_policy)
from zipline.finance import commission, slippage, cancel_policy
from zipline.utils.run_algo import run_algorithm
from lab.data import daily_from_5min, DOW

BUDGET = 10000.0
FEE = 0.0005
CAL = get_calendar("XNYS")

# ---------------- data (via lab.data only) ----------------
DATA, LAST_REAL = {}, {}
for s in DOW:
    d = daily_from_5min(s).sort_values("date").reset_index(drop=True)
    idx = pd.to_datetime(d.date.values)
    df = d[["open", "high", "low", "close", "volume"]].astype(float).copy(); df.index = idx
    last = idx[-1]
    nxt = CAL.next_session(last)          # sentinel session: O=H=L=C= last real close, volume 1
    df.loc[nxt] = [df.close.iloc[-1]] * 4 + [1.0]
    DATA[s] = df; LAST_REAL[s] = last
START = min(df.index[0] for df in DATA.values()); END = max(df.index[-1] for df in DATA.values())

def ingest(environ, asset_db_writer, minute_bar_writer, daily_bar_writer, adjustment_writer, calendar,
           start_session, end_session, cache, show_progress, output_dir):
    meta = pd.DataFrame({"symbol": DOW, "start_date": [DATA[s].index[0] for s in DOW],
                         "end_date": [DATA[s].index[-1] for s in DOW],
                         "auto_close_date": [DATA[s].index[-1] + pd.Timedelta(days=1) for s in DOW],
                         "exchange": "NYSE"})
    asset_db_writer.write(equities=meta)
    daily_bar_writer.write(((i, DATA[s]) for i, s in enumerate(DOW)), show_progress=False)
    adjustment_writer.write()

bundles.register("labdaily", ingest, calendar_name="XNYS", start_session=START, end_session=END)

class OpenFillFixedBudget(slippage.EquitySlippageModel):
    """Fill model: market orders fill at the bar's OPEN (zipline's built-ins use 'close'); buys are sized at
    FILL time as floor(BUDGET/open) (order amount is only an upper bound); sells fill the whole open amount."""
    def process_order(self, data, order_):
        px = data.current(order_.asset, "open")
        if order_.open_amount > 0:
            n = min(int(math.floor(BUDGET / px)), order_.open_amount)
            if n < 1:
                return None, None
            return px, n
        return px, order_.open_amount

def initialize(ctx):
    ctx.assets = [symbol(s) for s in DOW]
    ctx.nm = {a: s for a, s in zip(ctx.assets, DOW)}
    ctx.n = 0
    set_slippage(us_equities=OpenFillFixedBudget())
    set_commission(us_equities=commission.PerDollar(cost=FEE))
    set_cancel_policy(cancel_policy.NeverCancel())

def handle_data(ctx, data):
    ctx.n += 1
    # cancel the unfilled remainder of yesterday's (oversized) buy orders
    for a, oo in get_open_orders().items():
        for o in oo:
            if o.amount > 0:
                cancel_order(o)
    if ctx.n < 51:
        return
    today = data.current_dt.tz_localize(None).normalize() if data.current_dt.tzinfo else data.current_dt.normalize()
    px = data.history(ctx.assets, "close", 51, "1d")
    for a in ctx.assets:
        s = ctx.nm[a]
        if not data.can_trade(a):
            continue
        c = px[a].to_numpy()
        if np.isnan(c).any():
            continue
        s20, s50 = c[-20:].mean(), c[-50:].mean()
        p20, p50 = c[-21:-1].mean(), c[-51:-1].mean()
        pos = ctx.portfolio.positions.get(a)
        held = pos.amount if pos is not None else 0
        pending = get_open_orders(a)
        if today >= LAST_REAL[s]:
            if held > 0 and not pending and today == LAST_REAL[s]:
                order(a, -held)       # fills at sentinel session open == last real close
            continue
        if held == 0 and not pending:
            if s20 > s50 and p20 <= p50:
                order(a, 10**9)       # upper bound only; fill model sizes floor(BUDGET/open)
        elif held > 0 and not pending and s20 < s50:
            order(a, -held)

if __name__ == "__main__":
    bundles.ingest("labdaily", os.environ, pd.Timestamp.utcnow(), [], show_progress=False)
    res = run_algorithm(start=START, end=END, initialize=initialize, handle_data=handle_data,
                        capital_base=1e9, data_frequency="daily", bundle="labdaily",
                        trading_calendar=CAL, benchmark_returns=pd.Series(0.0, index=CAL.sessions_in_range(START, END)),
                        custom_loader=None)
    tx = []
    for dt, row in res.transactions.items():
        for t in row:
            tx.append((pd.Timestamp(t["dt"]).tz_localize(None).normalize() if pd.Timestamp(t["dt"]).tzinfo is None else pd.Timestamp(t["dt"]).tz_convert(None).normalize(),
                       t["sid"].symbol, t["amount"], t["price"], t["order_id"]))
    tx = pd.DataFrame(tx, columns=["day", "sym", "amt", "px", "oid"]).sort_values(["sym", "day"])
    rows = []
    for sym, g in tx.groupby("sym"):
        g = g.reset_index(drop=True)
        assert len(g) % 2 == 0 and (g.amt[::2] > 0).all() and (g.amt[1::2] < 0).all(), sym
        for i in range(0, len(g), 2):
            b, s_ = g.iloc[i], g.iloc[i + 1]
            assert b.amt == -s_.amt
            # engine fill prices/shares; net pnl = gross - PerDollar commission both sides (engine's commission model)
            pnl = (s_.px - b.px) * b.amt - FEE * b.px * b.amt - FEE * s_.px * b.amt
            ex = min(s_.day, LAST_REAL[sym])
            rows.append((sym, b.day.strftime("%Y-%m-%d"), b.px, ex.strftime("%Y-%m-%d"), s_.px, int(b.amt), pnl))
    out = pd.DataFrame(rows, columns="symbol,entry_time,entry_price,exit_time,exit_price,shares,pnl_net".split(","))
    os.makedirs("results/trades", exist_ok=True)
    out.to_csv("results/trades/zipline_S2.csv", index=False)
    print(len(out), out.pnl_net.sum())
    print("engine cash/pnl check: ending portfolio pnl =", float(res.portfolio_value.iloc[-1] - 1e9))
