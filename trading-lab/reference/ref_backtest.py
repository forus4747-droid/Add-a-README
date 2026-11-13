"""Independent reference implementation of S1 and S2 (protocol/STRATEGIES.md).
Deliberately plain Python loops, one bar at a time, no vectorised tricks, no third-party backtest code.
Output columns: symbol, entry_time, entry_price, exit_time, exit_price, shares, pnl_net"""
import math
FEE = 0.0005; NOTIONAL = 10000.0

def _trade(sym, et, ep, xt, xp):
    sh = math.floor(NOTIONAL / ep)
    pnl = sh * (xp - ep) - FEE * sh * ep - FEE * sh * xp
    return dict(symbol=sym, entry_time=et, entry_price=ep, exit_time=xt, exit_price=xp, shares=sh, pnl_net=round(pnl, 6))

def s1_orb(sym, bars):
    """bars: list of dicts with day, hm ('HH:MM'), time_new_york, open, high, low, close — sorted by time."""
    trades, days = [], {}
    for b in bars: days.setdefault(b["day"], []).append(b)
    for day in sorted(days):
        d = days[day]
        if len(d) < 78: continue
        rng = [b for b in d if "09:30" <= b["hm"] <= "09:55"]
        if len(rng) != 6: continue
        hi = max(b["high"] for b in rng); lo = min(b["low"] for b in rng)
        pos = None; traded = False; pending = None  # pending: 'buy' / 'sell' to execute at this bar's open
        for b in d:
            if pending == "buy":
                pos = (b["time_new_york"], b["open"]); traded = True
            elif pending == "sell" and pos:
                trades.append(_trade(sym, pos[0], pos[1], b["time_new_york"], b["open"])); pos = None
            pending = None
            if b["hm"] == "15:55":
                if pos: trades.append(_trade(sym, pos[0], pos[1], b["time_new_york"], b["open"])); pos = None
                break
            if pos is None and not traded and "10:00" <= b["hm"] <= "15:40" and b["close"] > hi:
                pending = "buy"
            elif pos is not None and b["close"] < lo and b["hm"] <= "15:45":
                pending = "sell"
    return trades

def s2_sma(sym, bars, fast=20, slow=50):
    """bars: list of dicts with date, open, close — daily, sorted."""
    trades, pos, pending = [], None, None
    closes = []; prev = None
    for i, b in enumerate(bars):
        if pending == "buy": pos = (b["date"], b["open"])
        elif pending == "sell" and pos:
            trades.append(_trade(sym, pos[0], pos[1], b["date"], b["open"])); pos = None
        pending = None
        closes.append(b["close"])
        if len(closes) >= slow:
            f = sum(closes[-fast:]) / fast; s = sum(closes[-slow:]) / slow
            if prev is not None:
                if pos is None and f > s and prev[0] <= prev[1]: pending = "buy"
                elif pos is not None and f < s: pending = "sell"
            prev = (f, s)
    if pos: trades.append(_trade(sym, pos[0], pos[1], bars[-1]["date"], bars[-1]["close"]))
    return trades
