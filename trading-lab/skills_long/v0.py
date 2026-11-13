"""v0 = the Phase 1 final swing skill, unchanged: score = -(rank of 1-day + 2-day + 5-day return)/3,
ranked across the in-universe stocks each day. No fitting."""
import pandas as pd
def predict(panel, market):
    p = panel.sort_values(["symbol", "date"]); g = p.groupby("symbol", sort=False).close
    f = pd.DataFrame({"symbol": p.symbol, "date": p.date, "r1": p.close / g.shift(1) - 1, "r2": p.close / g.shift(2) - 1, "r5": p.close / g.shift(5) - 1})[p.in_univ.values]
    r = f.groupby("date")[["r1", "r2", "r5"]].rank(pct=True) - 0.5
    return f[["symbol", "date"]].assign(score=(-r.mean(axis=1)).values).dropna()
