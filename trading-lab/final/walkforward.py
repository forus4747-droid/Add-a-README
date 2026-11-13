"""Model selection INSIDE TRAIN only (2016-2023). Walk-forward: for test year Y in 2019..2023, fit on all rows
whose label is known before Y starts, predict Y, score with the protocol scorer. Nothing here touches 2024+.
Writes results/04_walkforward.csv"""
import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.linear_model import Ridge
from lab.data import load_daily
from lab.score import swing_targets, score
from final.features import build, add_training_label
daily = load_daily(); daily = daily[daily.date <= "2023-12-31"]          # hard cut: TRAIN only
X, cols = build(daily); X = add_training_label(X, daily); T = swing_targets()
CONFIGS = {
 "ridge": dict(kind="ridge", alpha=1000.0),
 "gbm_small": dict(kind="gbm", n=200, lr=0.02, leaves=15, min_leaf=1000),
 "gbm_mid": dict(kind="gbm", n=400, lr=0.02, leaves=31, min_leaf=500),
 "gbm_slow": dict(kind="gbm", n=800, lr=0.01, leaves=15, min_leaf=1000),
}
def fit_predict(cfg, tr, te, seed=0):
    if cfg["kind"] == "ridge":
        m = Ridge(alpha=cfg["alpha"]).fit(tr[cols].values, tr.label.values); return m.predict(te[cols].values)
    p = np.zeros(len(te))
    for s in range(3):
        m = lgb.LGBMRegressor(n_estimators=cfg["n"], learning_rate=cfg["lr"], num_leaves=cfg["leaves"], min_child_samples=cfg["min_leaf"],
            subsample=0.7, subsample_freq=1, colsample_bytree=0.5, reg_lambda=10.0, random_state=seed + s, n_jobs=4, verbose=-1)
        m.fit(tr[cols].values, tr.label.values); p += m.predict(te[cols].values)
    return p / 3
if __name__ == "__main__":
    rows, P = [], {k: [] for k in CONFIGS}
    for Y in range(2019, 2024):
        tr = X[(X.label_end < f"{Y}-01-01") & X.label.notna()]; te = X[(X.date >= f"{Y}-01-01") & (X.date <= f"{Y}-12-31")]
        for k, cfg in CONFIGS.items():
            te_p = te[["symbol", "date"]].assign(score=fit_predict(cfg, tr, te)); P[k].append(te_p)
            m = score(te_p, T, (f"{Y}-01-01", f"{Y}-12-31")); rows.append(dict(config=k, year=Y, **m)); print(k, Y, m["rank_ic"], m["ic_tstat"], m["excess_net_ann"], flush=True)
    # blend = average of per-day ranks of ridge and the gbm configs
    for Y in range(2019, 2024):
        i = Y - 2019; b = P["ridge"][i][["symbol", "date"]].copy(); b["score"] = 0.0
        for k in ("ridge", "gbm_slow"): b["score"] += P[k][i].groupby("date").score.rank(pct=True).values
        m = score(b, T, (f"{Y}-01-01", f"{Y}-12-31")); rows.append(dict(config="blend_ridge_gbm_slow", year=Y, **m))
    r = pd.DataFrame(rows); r.to_csv("results/04_walkforward.csv", index=False)
    s = r.groupby("config").agg(mean_ic=("rank_ic", "mean"), min_ic=("rank_ic", "min"), years_pos=("rank_ic", lambda x: int((x > 0).sum())), mean_t=("ic_tstat", "mean"), mean_excess=("excess_net_ann", "mean"), years_excess_pos=("excess_net_ann", lambda x: int((x > 0).sum())))
    print(s.round(4).to_string())
