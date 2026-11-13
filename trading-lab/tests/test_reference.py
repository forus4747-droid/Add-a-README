"""Hand-computed cases for the reference backtester. Expected values worked out by hand in the comments."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from reference.ref_backtest import s1_orb, s2_sma

def day(prices, d="2024-01-02"):
    """78 bars from 09:30; prices = {hm: (o,h,l,c)}, default flat 100."""
    out = []
    for i in range(78):
        hm = f"{9 + (30 + 5 * i) // 60:02d}:{(30 + 5 * i) % 60:02d}"
        o, h, l, c = prices.get(hm, (100, 100, 100, 100))
        out.append(dict(day=d, hm=hm, time_new_york=f"{d} {hm}", open=o, high=h, low=l, close=c))
    return out

def test_s1_breakout_then_eod_exit():
    # range 09:30-09:55: high 101, low 99. 10:10 closes 101.5 > 101 -> buy 10:15 open (102). Exit 15:55 open (104).
    p = {"09:30": (100, 101, 99, 100), "10:10": (100, 101.5, 100, 101.5), "10:15": (102, 102, 102, 102), "15:55": (104, 104, 104, 104)}
    t = s1_orb("X", day(p))
    assert len(t) == 1 and t[0]["entry_time"].endswith("10:15") and t[0]["exit_time"].endswith("15:55")
    # shares = floor(10000/102) = 98; gross = 98*2 = 196; fees = 0.0005*98*(102+104) = 10.094; net = 185.906
    assert t[0]["shares"] == 98 and abs(t[0]["pnl_net"] - 185.906) < 1e-6

def test_s1_stop_and_one_trade_per_day():
    # buy 10:15 @102; 11:00 closes 98 < 99 -> sell 11:05 open (97). Later breakout at 12:00 must NOT re-enter.
    p = {"09:30": (100, 101, 99, 100), "10:10": (100, 101.5, 100, 101.5), "10:15": (102, 102, 102, 102),
         "11:00": (100, 100, 98, 98), "11:05": (97, 97, 97, 97), "12:00": (100, 103, 100, 103)}
    t = s1_orb("X", day(p))
    assert len(t) == 1 and t[0]["exit_time"].endswith("11:05") and t[0]["exit_price"] == 97

def test_s1_no_signal_uses_close_not_high():
    # 10:10 high pierces 101 but close 100.5 does not -> no trade
    p = {"09:30": (100, 101, 99, 100), "10:10": (100, 102, 100, 100.5)}
    assert s1_orb("X", day(p)) == []

def test_s1_skips_short_day_and_late_signal():
    assert s1_orb("X", day({"09:30": (100, 101, 99, 100), "10:10": (100, 102, 100, 102)})[:70]) == []
    # signal on 15:45 bar is after the 15:40 cutoff -> no trade
    assert s1_orb("X", day({"09:30": (100, 101, 99, 100), "15:45": (100, 102, 100, 102)})) == []

def test_s2_cross():
    # 50 days at 100 (SMA20 == SMA50, no cross), then rises 1/day. Day index 50 close 101: SMA20 100.05 > SMA50 100.02,
    # previous equal -> buy at day 51 open. Then falls 5/day from day 60: SMA20 < SMA50 first at close of day k -> sell next open.
    closes = [100] * 50 + [101 + i for i in range(10)] + [110 - 5 * (i + 1) for i in range(15)]
    bars = [dict(date=f"d{i:03d}", open=c, close=c) for i, c in enumerate(closes)]
    t = s2_sma("X", bars)
    assert len(t) == 1 and t[0]["entry_time"] == "d051" and t[0]["entry_price"] == 102
    # find sell by hand: first day where SMA20 < SMA50
    k = next(i for i in range(60, len(closes)) if sum(closes[i-19:i+1]) / 20 < sum(closes[i-49:i+1]) / 50)
    assert t[0]["exit_time"] == f"d{k+1:03d}"

def test_s2_open_position_closed_at_end():
    closes = [100] * 50 + [101 + i for i in range(10)]
    bars = [dict(date=f"d{i:03d}", open=c, close=c) for i, c in enumerate(closes)]
    t = s2_sma("X", bars)
    assert len(t) == 1 and t[0]["exit_time"] == "d059" and t[0]["exit_price"] == 110
