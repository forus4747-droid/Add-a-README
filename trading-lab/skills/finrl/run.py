"""FinRL Stock_NeurIPS2018 pipeline (PPO + A2C) on lab data. Entry: python skills/finrl/run.py
Train 2016-01-01..2023-12-31, 50k steps each, seed 42, FinRL default hyper-params. Trade 2024-2025 day by day."""
import sys, os, warnings, json, random
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, ROOT); os.chdir(ROOT)
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, torch
from lab.data import load_daily, DOW
from finrl.config import INDICATORS, PPO_PARAMS, A2C_PARAMS
from finrl.meta.preprocessor.preprocessors import FeatureEngineer, data_split
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
from finrl.agents.stablebaselines3.models import DRLAgent
from stable_baselines3 import PPO, A2C

SEED = 42; STEPS = 50_000; INIT = 1_000_000; HMAX = 100; COST = 0.001; RS = 1e-4; TURB_THR = 70
TRAIN = ("2016-01-01", "2024-01-01"); TRADE = ("2024-01-01", "2026-01-01")   # data_split end is exclusive
OUT = "results"; MODELDIR = "skills/finrl/models"; os.makedirs(MODELDIR, exist_ok=True)

def build_raw():
    d = load_daily(); d = d[d.symbol.isin(DOW)].copy()
    full = d.groupby("symbol").date.count(); drop = full[full < full.max()].index.tolist()   # WBA (delisted 2025-08-27)
    d = d[~d.symbol.isin(drop)]
    d = d.rename(columns={"symbol": "tic"})
    d["day"] = pd.to_datetime(d.date).dt.dayofweek
    return d[["date", "tic", "open", "high", "low", "close", "volume", "day"]].sort_values(["date", "tic"]).reset_index(drop=True), drop

def preprocess(raw):
    fe = FeatureEngineer(use_technical_indicator=True, tech_indicator_list=INDICATORS, use_vix=False, use_turbulence=True, user_defined_feature=False)
    return fe.preprocess_data(raw).sort_values(["date", "tic"]).reset_index(drop=True)

def env_kwargs(df):
    n = len(df.tic.unique())
    return dict(stock_dim=n, hmax=HMAX, initial_amount=INIT, num_stock_shares=[0] * n, buy_cost_pct=[COST] * n, sell_cost_pct=[COST] * n,
                reward_scaling=RS, state_space=1 + 2 * n + len(INDICATORS) * n, action_space=n, tech_indicator_list=INDICATORS)

def seed_all():
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.set_num_threads(1)

def train(proc):
    tr = data_split(proc, *TRAIN)
    env, _ = StockTradingEnv(df=tr, **env_kwargs(tr)).get_sb_env()
    models = {}
    for name, P, params in (("ppo", "ppo", PPO_PARAMS), ("a2c", "a2c", A2C_PARAMS)):
        seed_all(); ag = DRLAgent(env=env)
        m = ag.get_model(P, model_kwargs=dict(params), seed=SEED, verbose=0)
        m = ag.train_model(m, tb_log_name=name, total_timesteps=STEPS); m.save(f"{MODELDIR}/{name}"); models[name] = m
    return models

def trade(model, proc, start, end):
    """Day-by-day run, deterministic. Returns dates, tics, raw actions [T,N], account values [T], turbulence."""
    te = data_split(proc, start, end); env = StockTradingEnv(df=te, turbulence_threshold=TURB_THR, risk_indicator_col="turbulence", **env_kwargs(te))
    tics = list(te.tic.unique()[:]) ; T = len(te.index.unique())
    obs, _ = env.reset(); acts = []
    for i in range(T):
        a, _ = model.predict(np.array(obs, dtype=np.float32), deterministic=True); a = np.asarray(a).reshape(-1)
        acts.append(a.copy())
        if i == T - 1: break
        obs, *_ = env.step(a)
    dates = [str(x) for x in env.date_memory[:T]]
    return dates, tics, np.array(acts), np.array(env.asset_memory[:T]), env

def ew(raw, start, end):
    p = raw[(raw.date >= start) & (raw.date < end)].pivot(index="date", columns="tic", values="close")
    return (p / p.iloc[0]).mean(axis=1) * INIT   # equal $ per name at first close, held

if __name__ == "__main__":
    raw, dropped = build_raw(); proc = preprocess(raw)
    print("dropped", dropped, "tics", raw.tic.nunique(), "rows", len(proc))
    models = train(proc)
    res = {}; accts = {}; preds = {}
    for k, m in models.items():
        # (a) continuous 2024-2025 run -> predictions + 2024 account
        dts, tics, A, acc, env = trade(m, proc, "2024-01-01", "2026-01-01")
        preds[k] = pd.DataFrame([(t, d, float(A[i, j])) for i, d in enumerate(dts) for j, t in enumerate(tics)], columns=["symbol", "date", "score"])
        preds[k].to_parquet(f"{OUT}/preds/finrl_{k}_swing.parquet", index=False)
        s = pd.Series(acc, index=dts); res[k] = {"dts": dts, "cont": s}
        # (b) 2025 restart at $1M
        d25, _, _, acc25, _ = trade(m, proc, "2025-01-01", "2026-01-01"); accts[k] = (pd.Series(acc, index=dts)[[d for d in dts if d < "2025-01-01"]], pd.Series(acc25, index=d25))
        np.save(f"{OUT}/finrl_{k}_actions.npy", A)
    e24 = ew(raw, "2024-01-01", "2025-01-01"); e25 = ew(raw, "2025-01-01", "2026-01-01")
    idx = list(e24.index) + list(e25.index)
    df = pd.DataFrame({"date": idx, "ppo_account": pd.concat(accts["ppo"]).values, "a2c_account": pd.concat(accts["a2c"]).values,
                       "equal_weight_buy_hold": np.concatenate([e24.values, e25.values])})
    df.to_csv(f"{OUT}/finrl_account_values.csv", index=False)
    summ = {}
    for nm, lo, hi in (("2024_DEV", "2024-01-01", "2025-01-01"), ("2025_VAL", "2025-01-01", "2026-01-01")):
        x = df[(df.date >= lo) & (df.date < hi)]
        summ[nm] = {c: round(float(x[c].iloc[-1] / x[c].iloc[0] - 1), 4) for c in ["ppo_account", "a2c_account", "equal_weight_buy_hold"]}
        summ[nm]["first"], summ[nm]["last"] = x.date.iloc[0], x.date.iloc[-1]
    summ["meta"] = dict(dropped=dropped, n_tics=int(raw.tic.nunique()), steps=STEPS, seed=SEED, cost=COST, hmax=HMAX, turb_threshold=TURB_THR,
                        turbulence_days_ge_thr_trade=int((proc[(proc.date >= "2024-01-01")].drop_duplicates("date").turbulence >= TURB_THR).sum()))
    json.dump(summ, open(f"{OUT}/finrl_summary.json", "w"), indent=1); print(json.dumps(summ, indent=1))
