"""Walk-forward models: base rate, analogs, ridge logit, shrinkage blend. Only resolved outcomes are used."""
import hashlib
import os
import pickle

import numpy as np
import pandas as pd

from . import MODEL_VERSION, ROOT
from .features import ANALOG_COLS
from .targets import EVENTS, HORIZONS

W_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]
K_ANALOG = 60
LAMBDA = 1.0
MIN_TRAIN = 120
START = "1950-01-01"
SPLIT = pd.Timestamp("1999-12-31")


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def fit_ridge_logit(Xs, y, lam=LAMBDA, iters=60):
    n, d = Xs.shape
    A = np.hstack([np.ones((n, 1)), Xs])
    P = lam * np.eye(d + 1)
    P[0, 0] = 0.0
    b = np.zeros(d + 1)
    for _ in range(iters):
        p = sigmoid(A @ b)
        W = np.clip(p * (1 - p), 1e-6, None)
        g = A.T @ (y - p) - P @ b
        H = A.T @ (A * W[:, None]) + P
        step = np.linalg.solve(H, g)
        b += step
        if np.max(np.abs(step)) < 1e-9:
            break
    return b


class _Fit:
    def __init__(self, X, y):
        self.mu = X.mean(0)
        self.sd = X.std(0)
        self.sd[self.sd == 0] = 1.0
        self.b = fit_ridge_logit((X - self.mu) / self.sd, y)

    def predict(self, x):
        z = (x - self.mu) / self.sd
        return float(sigmoid(self.b[0] + z @ self.b[1:]))


def _arrays(F, T, q):
    X = F[ANALOG_COLS].values.astype(float)
    valid = ~np.isnan(X).any(1)
    ridx = T["idx"].values.astype(int)
    y = T[q].values.astype(float)
    return X, valid, ridx, y


def walk(F, T, q, ks=None, start=START, refit_every=12):
    """Predict at each row k in ks (default: all rows from `start`). Uses only rows whose outcome window
    ended on or before row k's date."""
    h = HORIZONS[EVENTS[q][0]]
    X, valid, ridx, y = _arrays(F, T, q)
    if ks is None:
        dts = pd.DatetimeIndex(F["date"])
        ks = [k for k in range(len(F)) if dts[k] >= pd.Timestamp(start) and valid[k] and ridx[k] >= 0]
    out = []
    fit = None
    for c, k in enumerate(ks):
        tr = np.where(valid[:k] & (ridx[:k] >= 0) & (ridx[:k] + h <= ridx[k]) & ~np.isnan(y[:k]))[0]
        if len(tr) < MIN_TRAIN:
            continue
        base = float(y[tr].mean())
        vv = valid[: k + 1]
        mu = X[: k + 1][vv].mean(0)
        sd = X[: k + 1][vv].std(0)
        sd[sd == 0] = 1.0
        Z = (X[: k + 1] - mu) / sd
        d = ((Z[tr] - Z[k]) ** 2).sum(1)
        kk = min(K_ANALOG, len(tr))
        nn = tr[np.argpartition(d, kk - 1)[:kk]] if kk < len(tr) else tr
        analog = float(y[nn].mean())
        if fit is None or c % refit_every == 0 or len(ks) == 1:
            fit = _Fit(X[tr], y[tr])
        logit = fit.predict(X[k])
        out.append((k, base, analog, logit))
    df = pd.DataFrame(out, columns=["k", "base", "analog", "logit"])
    if len(df):
        df["model"] = (df["analog"] + df["logit"]) / 2
        df["date"] = pd.DatetimeIndex(F["date"])[df["k"].values]
        df["y"] = y[df["k"].values]
        df["res_idx"] = ridx[df["k"].values] + h
    return df


def final_p(base, model, w):
    return np.clip(base + w * (model - base), 0.0, 1.0)


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def calibration(p, y, bins=5):
    o = np.argsort(p, kind="stable")
    res = []
    for part in np.array_split(o, bins):
        if len(part):
            res.append({"n": int(len(part)), "mean_pred": float(p[part].mean()), "obs_freq": float(y[part].mean())})
    return res


def n_episodes(dates_idx, y):
    """Number of distinct runs of consecutive scored months with outcome 1."""
    runs, prev = 0, None
    for i, v in zip(dates_idx, y):
        if v == 1:
            if prev is None or i != prev + 1:
                runs += 1
            prev = i
        else:
            prev = None
    return runs


def summarize(df, w, label_mask):
    d = df[label_mask & df["y"].notna()]
    if len(d) == 0:
        return None
    y = d["y"].values
    pf = final_p(d["base"].values, d["model"].values, w)
    bb = brier(d["base"].values, y)
    out = {"n_months": int(len(d)), "event_rate": float(y.mean()), "n_event_months": int(y.sum()),
           "n_event_episodes": n_episodes(d["k"].values, y), "w": w,
           "brier_base": bb, "brier_analog": brier(d["analog"].values, y), "brier_logit": brier(d["logit"].values, y),
           "brier_model": brier(d["model"].values, y), "brier_final": brier(pf, y)}
    out["skill_analog"] = 1 - out["brier_analog"] / bb if bb > 0 else None
    out["skill_logit"] = 1 - out["brier_logit"] / bb if bb > 0 else None
    out["skill_final"] = 1 - out["brier_final"] / bb if bb > 0 else None
    out["calibration"] = calibration(pf, y)
    return out


def choose_w(df, mask):
    d = df[mask & df["y"].notna()]
    if len(d) == 0:
        return 0.0
    best, bw = None, 0.0
    for w in W_GRID:
        b = brier(final_p(d["base"].values, d["model"].values, w), d["y"].values)
        if best is None or b < best - 1e-12:
            best, bw = b, w
    return bw


def backtest_question(F, T, g, q):
    df = walk(F, T, q)
    n = len(g)
    res_date = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    ok = df["res_idx"] < n
    res_date[ok] = g.index[df.loc[ok, "res_idx"].values]
    df["res_date"] = res_date
    pre = (df["date"] <= SPLIT) & (df["res_date"] <= SPLIT)    # outcomes fully known by end of 1999
    hold = df["date"] > SPLIT
    w_pre = choose_w(df, pre)
    w_all = choose_w(df, df["y"].notna())
    return {"df": df, "w_pre": w_pre, "w_all": w_all,
            "pre_1950_1999": summarize(df, w_pre, pre),
            "holdout_2000_latest": summarize(df, w_pre, hold),
            "holdout_2000_latest_w_all": summarize(df, w_all, hold),
            "all_w_all": summarize(df, w_all, df["date"] >= pd.Timestamp(START))}


def features_hash(F, T):
    h = hashlib.sha256()
    h.update(MODEL_VERSION.encode())
    h.update(pd.util.hash_pandas_object(F.drop(columns=["date"]).reset_index(drop=True), index=False).values.tobytes())
    h.update(pd.util.hash_pandas_object(T.reset_index(drop=True), index=False).values.tobytes())
    return h.hexdigest()


def backtest(F, T, g, root=None, use_cache=True):
    cdir = os.path.join(root or ROOT, "state", "cache")
    os.makedirs(cdir, exist_ok=True)
    path = os.path.join(cdir, "backtest.pkl")
    key = features_hash(F, T)
    if use_cache and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                c = pickle.load(f)
            if c.get("key") == key:
                return c["res"], True
        except Exception:
            pass
    res = {q: backtest_question(F, T, g, q) for q in EVENTS}
    with open(path, "wb") as f:
        pickle.dump({"key": key, "res": res}, f)
    return res, False


def live_predict(F, T, q, k=None):
    """Prediction at the last feature row (or row k) using everything resolved so far."""
    k = len(F) - 1 if k is None else k
    df = walk(F, T, q, ks=[k])
    if len(df) == 0:
        return None
    r = df.iloc[0]
    return {"base": float(r["base"]), "analog": float(r["analog"]), "logit": float(r["logit"]),
            "model": float(r["model"])}


def closest_analogs(F, T, n=15, gap_months=3):
    X = F[ANALOG_COLS].values.astype(float)
    valid = ~np.isnan(X).any(1)
    k = len(F) - 1
    if not valid[k]:
        return None
    mu = X[valid].mean(0)
    sd = X[valid].std(0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    cand = np.where(valid & T["fwd_ret_252"].notna().values & (np.arange(len(F)) < k))[0]
    d = np.sqrt(((Z[cand] - Z[k]) ** 2).sum(1))
    sel = cand[np.argsort(d)[:n]]
    dist = dict(zip(cand, d))
    sel = sorted(sel)
    groups, cur = [], []
    for i in sel:
        if cur and i - cur[-1] > gap_months:
            groups.append(cur)
            cur = []
        cur.append(i)
    if cur:
        groups.append(cur)
    out = []
    for gr in groups:
        months = [{"month": str(F.index[i]), "date": str(pd.Timestamp(F["date"].iloc[i]).date()),
                   "distance": float(dist[i]), "next_12m_return": float(T["fwd_ret_252"].iloc[i]),
                   "worst_drawdown_12m": float(T["fwd_min_252"].iloc[i])} for i in gr]
        out.append({"first": months[0]["month"], "last": months[-1]["month"], "n_months": len(gr),
                    "mean_distance": float(np.mean([m["distance"] for m in months])),
                    "mean_next_12m_return": float(np.mean([m["next_12m_return"] for m in months])),
                    "worst_drawdown_12m": float(min(m["worst_drawdown_12m"] for m in months)),
                    "months": months})
    out.sort(key=lambda r: r["mean_distance"])
    return out


def cape_ten_year_estimate(F, T):
    """OLS of annualised 10y real total return on ln(CAPE) (overlapping windows, in-sample)."""
    d = pd.DataFrame({"x": np.log(F["cape"]), "y": T["real_tr_10y"], "est": F["cape_is_estimate"]}).dropna()
    if len(d) < 60:
        return None
    A = np.c_[np.ones(len(d)), d["x"].values]
    beta, *_ = np.linalg.lstsq(A, d["y"].values, rcond=None)
    res = d["y"].values - A @ beta
    sd = float(res.std(ddof=2))
    r2 = float(1 - res.var() / d["y"].var())
    cur = F.iloc[-1]
    x0 = np.log(cur["cape"])
    est = float(beta[0] + beta[1] * x0)
    q16, q84 = np.quantile(res, [0.16, 0.84])
    return {"cape_now": float(cur["cape"]), "cape_is_estimate": bool(cur["cape_is_estimate"]),
            "estimate_real_ann_10y": est, "band_1sd": [est - sd, est + sd], "resid_sd": sd,
            "band_empirical_16_84": [est + float(q16), est + float(q84)],
            "intercept": float(beta[0]), "slope_ln_cape": float(beta[1]), "r2": r2, "n_months": int(len(d)),
            "fit_first": str(d.index[0]), "fit_last": str(d.index[-1]),
            "note": "in-sample OLS on overlapping windows; effective independent samples ~ n/120"}
