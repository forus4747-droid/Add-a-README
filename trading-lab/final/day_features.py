"""Final skill — day features for the Dow 30. For (symbol, day) every input is known by 09:59:59 that day:
the six bars 09:30-09:55 and earlier days. Target (scoring only) is 10:00 open -> 15:55 open."""
import numpy as np, pandas as pd
from lab.data import DOW

def build(loader):
    out = []
    for s in DOW:
        m = loader(s); n = m.groupby("day").size(); full = n[n == 78].index
        g = m.groupby("day"); first = m[m.hm <= "09:55"].groupby("day")
        f = pd.DataFrame({"open": g.open.first(), "prev_close": g.close.last().shift(1), "c955": first.close.last(),
                          "hi30": first.high.max(), "lo30": first.low.min(), "vol30": first.volume.sum(), "dayvol": g.volume.sum()})
        f["gap"] = f.open / f.prev_close - 1; f["first30"] = f.c955 / f.open - 1; f["range30"] = f.hi30 / f.lo30 - 1
        f["relvol30"] = f.vol30 / f.vol30.shift(1).rolling(20, min_periods=10).mean()
        f["prev_day_ret"] = (g.close.last() / g.open.first() - 1).shift(1)
        f["since_prev_close"] = f.c955 / f.prev_close - 1
        f = f.loc[f.index.isin(full)].reset_index().rename(columns={"day": "date"}); f.insert(0, "symbol", s); out.append(f)
    X = pd.concat(out, ignore_index=True)
    cols = ["gap", "first30", "range30", "relvol30", "prev_day_ret", "since_prev_close"]
    X[cols] = X.groupby("date")[cols].rank(pct=True) - 0.5
    return X.dropna(subset=cols)[["symbol", "date"] + cols], cols
