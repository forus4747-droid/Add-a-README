"""Freqtrade sample strategy + default-template rule sets as buy/sell signal predictors (no engine, no exchange).
Usage: PYF skills/ftsample/run.py [build|trunc]   (PYF = freqtrade env python; run from trading-lab/)
Signals come from each strategy class's OWN populate_indicators/populate_entry_trend/populate_exit_trend,
called on a DataFrame [date,open,high,low,close,volume]; class instantiated with a minimal config dict
({'strategy': name, 'runmode': 'other', 'timeframe': ..., 'stake_currency': 'USD', 'dry_run': True}) -> default param values (.value).
score = +1 enter_long, -1 exit_long or enter_short, 0 if none/both."""
import sys, os, importlib.util, pathlib, random
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from lab.data import DOW, load_5min, load_daily
HERE = pathlib.Path(__file__).parent
SKILLS = {"ftsample": ("SampleStrategy", None), "ft_minimal": ("FtMinimal", HERE / "rendered/FtMinimal.py"),
          "ft_full": ("FtFull", HERE / "rendered/FtFull.py")}
_cache = {}
def strat(skill, tf):
    if (skill, tf) in _cache: return _cache[skill, tf]
    cls, path = SKILLS[skill]
    if path is None:
        from freqtrade.templates.sample_strategy import SampleStrategy as C
    else:
        spec = importlib.util.spec_from_file_location(cls, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); C = getattr(m, cls)
    s = C({"strategy": cls, "runmode": "other", "timeframe": "5m", "stake_currency": "USD", "dry_run": True})
    _cache[skill, tf] = s; return s

def signals(skill, df, tf="5m"):
    """df: date,open,high,low,close,volume (continuous real bars). Returns int Series score aligned to df."""
    s = strat(skill, tf); d = df.copy().reset_index(drop=True)
    d = s.populate_indicators(d, {"pair": "X"}); d = s.populate_entry_trend(d, {"pair": "X"}); d = s.populate_exit_trend(d, {"pair": "X"})
    z = lambda c: (d[c].fillna(0) == 1) if c in d else pd.Series(False, index=d.index)
    buy = z("enter_long"); sell = z("exit_long") | z("enter_short")
    return (buy.astype(int) - sell.astype(int)).where(~(buy & sell), 0).values

def bars5(sym):
    m = load_5min(sym).sort_values("time_new_york").reset_index(drop=True)
    m["date"] = pd.to_datetime(m.time_new_york.str[:16]); return m
def dbars(g):
    g = g.sort_values("date").reset_index(drop=True); g["tdate"] = g.date; g["date"] = pd.to_datetime(g.date); return g
COLS = ["date", "open", "high", "low", "close", "volume"]

def build(skill):
    rows = []
    for sym in DOW:
        m = bars5(sym); sc = signals(skill, m[COLS]); m["score"] = sc
        k = m[(m.score != 0) & (m.day >= "2024-07-01") & (m.day <= "2025-12-31")]
        rows.append(pd.DataFrame({"symbol": sym, "time": k.time_new_york.str[:16], "score": k.score.astype(int)}))
    out = pd.concat(rows, ignore_index=True); out.to_parquet(f"results/preds/{skill}_bar.parquet", index=False)
    rate = out.assign(yr=out.time.str[:4]).groupby(["yr", "score"]).size().unstack(fill_value=0)
    print(skill, "bar signals:\n", rate, "\nper symbol-year (5m): buy %.1f sell %.1f (2025)" % (rate.loc["2025", 1] / 30, rate.loc["2025", -1] / 30 if -1 in rate else 0))
    D = load_daily(stocks_only=True); rows = []
    for sym, g in D.groupby("symbol"):
        g = dbars(g); g["score"] = signals(skill, g[COLS], "1d")
        k = g[(g.score != 0) & (g.tdate >= "2024-01-01") & (g.tdate <= "2025-12-31")]
        rows.append(pd.DataFrame({"symbol": sym, "date": k.tdate, "score": k.score.astype(int)}))
    o = pd.concat(rows, ignore_index=True); o.to_parquet(f"results/preds/{skill}_swing.parquet", index=False)
    ns = D.symbol.nunique(); r = o.assign(yr=o.date.str[:4]).groupby(["yr", "score"]).size().unstack(fill_value=0)
    print(skill, "daily signals:\n", r, "\nper symbol-year: ", (r / ns).round(2).to_dict("index"))

def trunc(skill, seed=7):
    rnd = random.Random(seed); res = []
    full = {s: bars5(s) for s in DOW}
    for _ in range(3):  # 5m: pick random fired-or-not bar; bias to include one firing bar
        sym = rnd.choice(DOW); m = full[sym]; sc = signals(skill, m[COLS])
        cand = np.where((sc != 0) & (m.day >= "2024-07-01") & (m.day <= "2025-12-31"))[0] if _ == 0 else np.where((m.day >= "2024-07-01") & (m.day <= "2025-12-31"))[0]
        i = int(rnd.choice(list(cand))); sc2 = signals(skill, m.iloc[:i + 1][COLS])
        res.append(("bar", sym, m.time_new_york[i][:16], int(sc[i]), int(sc2[-1]), int(sc[i]) == int(sc2[-1])))
    D = load_daily(stocks_only=True); syms = sorted(D.symbol.unique())
    for j in range(3):
        sym = rnd.choice(syms); g = dbars(D[D.symbol == sym]); sc = signals(skill, g[COLS], "1d")
        cand = np.where((sc != 0) & (g.tdate >= "2024-01-01") & (g.tdate <= "2025-12-31"))[0] if j == 0 else np.where((g.tdate >= "2024-01-01") & (g.tdate <= "2025-12-31"))[0]
        i = int(rnd.choice(list(cand))); sc2 = signals(skill, g.iloc[:i + 1][COLS], "1d")
        res.append(("swing", sym, g.tdate[i], int(sc[i]), int(sc2[-1]), int(sc[i]) == int(sc2[-1])))
    print(skill, "TRUNCATION (mode,symbol,time,full,truncated,equal)"); [print(" ", r) for r in res]
    return res

if __name__ == "__main__":
    mode = sys.argv[1]; skills = sys.argv[2:] or list(SKILLS)
    for k in skills: (build if mode == "build" else trunc)(k)
