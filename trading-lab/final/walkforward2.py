"""Round 2 of TRAIN-only selection (2016-2023), after results/04_feature_stability.csv showed:
 (1) short-term reversal features have the same sign in 8 of 8 years;
 (2) size/liquidity features (dollar_vol63, amihud21) look best but are contaminated: the universe was chosen by
     2022-H2 dollar volume, so earlier-small stocks in it are survivors that grew. They are EXCLUDED.
Candidates: two fixed formulas and two models on restricted feature sets. Writes results/04_walkforward2.csv"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from final.walkforward import X, cols, T, fit_predict, score
BANNED = ["dollar_vol63", "amihud21"]
SHORT = ["ret1", "ret2", "ret5", "ret10", "gap", "intraday", "clv", "clv5", "rel_vol1", "rel_vol5", "ret_x_volchg5", "res_ret5",
         "vol5", "vol_ratio", "bb_pos", "rsi14", "dist_high21", "ma_dist20", "minret21", "maxret21"]
ALLOWED = [c for c in cols if c not in BANNED]
FORMULA = {"rev_simple": ["ret1", "ret2", "ret5"], "rev_plus": ["ret1", "ret2", "ret5", "intraday", "ret_x_volchg5", "res_ret5"]}
GB = dict(kind="gbm", n=200, lr=0.02, leaves=15, min_leaf=1000)
import final.walkforward as W
rows = []
for Y in range(2016, 2024):
    te = X[(X.date >= f"{Y}-01-01") & (X.date <= f"{Y}-12-31")]; rng = (f"{Y}-01-01", f"{Y}-12-31")
    for k, fs in FORMULA.items():
        m = score(te[["symbol", "date"]].assign(score=-te[fs].mean(axis=1).values), T, rng); rows.append(dict(config=k, year=Y, **m))
    if Y >= 2019:
        tr = X[(X.label_end < f"{Y}-01-01") & X.label.notna()]
        for k, fs in (("gbm_no_size", ALLOWED), ("gbm_short", SHORT), ("ridge_short", SHORT)):
            W.cols = fs; cfg = GB if k.startswith("gbm") else dict(kind="ridge", alpha=1000.0)
            m = score(te[["symbol", "date"]].assign(score=fit_predict(cfg, tr, te)), T, rng); rows.append(dict(config=k, year=Y, **m)); print(k, Y, m["rank_ic"], m["ic_tstat"], m["excess_net_ann"], flush=True)
r = pd.DataFrame(rows); r.to_csv("results/04_walkforward2.csv", index=False)
for lab, q in (("2019-2023", r[r.year >= 2019]), ("2016-2023 (formulas only)", r[r.config.str.startswith("rev")])):
    s = q.groupby("config").agg(mean_ic=("rank_ic", "mean"), min_ic=("rank_ic", "min"), years_pos=("rank_ic", lambda x: int((x > 0).sum())), n=("year", "count"), mean_t=("ic_tstat", "mean"), mean_excess=("excess_net_ann", "mean"), years_excess_pos=("excess_net_ann", lambda x: int((x > 0).sum())))
    print(lab); print(s.round(4).to_string())
