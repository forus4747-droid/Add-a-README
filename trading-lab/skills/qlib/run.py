"""Qlib standard pipeline (Alpha158 + LightGBM) -> results/preds/qlib_swing.parquet.
Modes:  run.py            full run (dump, train, predict, truncation tests)
        run.py --trunc SYM DATE OUT.json   (internal) rebuild dataset from data cut at DATE, score with saved model
"""
import sys, os, json, pickle, subprocess, shutil, random, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import numpy as np, pandas as pd
from lab.data import load_daily

TMP = "/tmp/qlib_work"; SRC = "/tmp/qlib_src"; PY = sys.executable
SEED = 42
START, END = "2016-01-01", "2025-12-31"
TRAIN_END, VALID_START, VALID_END, TEST_START = "2022-12-31", "2023-01-01", "2023-12-31", "2024-01-01"
H = 6  # label = Ref($open,-6)/Ref($open,-1)-1  -> uses prices up to t+6
LABEL = (["Ref($open, -6)/Ref($open, -1) - 1"], ["LABEL0"])
# Hyper-parameters: examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml (task.model.kwargs); num_threads 20->4 (machine has 4 cores; no effect on result semantics)
LGB = dict(loss="mse", colsample_bytree=0.8879, learning_rate=0.2, subsample=0.8789, lambda_l1=205.6999,
           lambda_l2=580.9768, max_depth=8, num_leaves=210, num_threads=4, seed=SEED)

def build_csv_and_dump(qdir, last_date=None):
    d = load_daily(stocks_only=True).sort_values(["symbol", "date"])
    if last_date: d = d[d.date <= last_date]
    d = d.assign(factor=1.0, vwap=(d.high + d.low + d.close) / 3)  # no VWAP in our data: typical price (H+L+C)/3
    csv = qdir + "_csv"
    for p in (qdir, csv): shutil.rmtree(p, ignore_errors=True)
    os.makedirs(csv)
    for s, g in d.groupby("symbol"):
        g.to_csv(f"{csv}/{s}.csv", index=False)
    subprocess.run([PY, f"{SRC}/scripts/dump_bin.py", "dump_all", "--data_path", csv, "--qlib_dir", qdir, "--freq", "day",
                    "--date_field_name", "date", "--symbol_field_name", "symbol", "--exclude_fields", "date,symbol",
                    "--file_suffix", ".csv"], check=True, capture_output=True)
    shutil.rmtree(csv)
    return d

def make_handler_cfg(end_time, seg=None):
    return dict(start_time=START, end_time=end_time, fit_start_time=START, fit_end_time=TRAIN_END,
                instruments="all", label=LABEL)

def make_dataset(qdir, end_time, segments):
    import qlib
    from qlib.config import REG_US
    from qlib.utils import init_instance_by_config
    # mlflow in this env refuses the default file store ('./mlruns'); route Qlib's recorder to sqlite (logging only, no effect on results)
    qlib.init(provider_uri=qdir, region=REG_US, exp_manager={"class": "MLflowExpManager", "module_path": "qlib.workflow.expm",
              "kwargs": {"uri": f"sqlite:///{TMP}/mlflow.db", "default_exp_name": "Experiment"}})
    return init_instance_by_config({"class": "DatasetH", "module_path": "qlib.data.dataset", "kwargs": {
        "handler": {"class": "Alpha158", "module_path": "qlib.contrib.data.handler", "kwargs": make_handler_cfg(end_time)},
        "segments": segments}})

def trading_days_before(cal, last, n):
    cal = [c for c in cal if c <= last]; return cal[-1 - n]

def main_trunc(sym, date, out):
    qdir = f"{TMP}/trunc_{sym}_{date}"
    build_csv_and_dump(qdir, last_date=date)
    ds = make_dataset(qdir, date, {"test": (date, date)})
    from qlib.data.dataset.handler import DataHandlerLP
    X = ds.prepare("test", col_set="feature", data_key=DataHandlerLP.DK_I)
    model = pickle.load(open(f"{TMP}/model.pkl", "rb"))
    sc = model.predict(ds, segment="test")
    row = X.xs(sym, level="instrument").iloc[0]; s = float(sc.xs(sym, level="instrument").iloc[0])
    json.dump(dict(score=s, features=row.to_dict()), open(out, "w")); shutil.rmtree(qdir)

def main():
    os.makedirs(TMP, exist_ok=True); os.makedirs(f"{ROOT}/results/preds", exist_ok=True)
    full = f"{TMP}/full"
    d = build_csv_and_dump(full)
    cal = sorted(d.date.unique())
    # purge: label at t reaches t+6 trading days; segments end so that NO train/valid label uses a price after its segment end
    train_last = trading_days_before(cal, TRAIN_END, H)
    valid_last = trading_days_before(cal, VALID_END, H)
    print("train segment", START, train_last, "| valid", VALID_START, valid_last, "| test", TEST_START, END)
    seg = {"train": (START, train_last), "valid": (VALID_START, valid_last), "test": (TEST_START, END)}
    ds = make_dataset(full, END, seg)
    from qlib.contrib.model.gbdt import LGBModel
    from qlib.data.dataset.handler import DataHandlerLP
    model = LGBModel(**LGB)   # early_stopping_rounds=50, num_boost_round=1000 are LGBModel defaults (as in the benchmark)
    model.fit(ds)
    pickle.dump(model, open(f"{TMP}/model.pkl", "wb"))
    print("best_iteration", model.model.best_iteration)
    # sanity: max date of label-bearing rows actually used in train/valid
    for k in ("train", "valid"):
        idx = ds.prepare(k, col_set="label", data_key=DataHandlerLP.DK_L).index.get_level_values("datetime")
        print(k, "rows", len(idx), "date range", idx.min().date(), idx.max().date())
    pred = model.predict(ds, segment="test")
    out = pred.rename("score").reset_index()
    out["date"] = out.datetime.dt.strftime("%Y-%m-%d"); out["symbol"] = out.instrument.astype(str)
    sym_ok = set(d.symbol); out["symbol"] = out.symbol.map({s.upper(): s for s in sym_ok}).fillna(out.symbol)
    out = out[["symbol", "date", "score"]].dropna()
    out = out[(out.date >= TEST_START) & (out.date <= END)]
    assert set(out.symbol) <= sym_ok, set(out.symbol) - sym_ok
    out.to_parquet(f"{ROOT}/results/preds/qlib_swing.parquet", index=False)
    print("preds", out.shape, out.symbol.nunique(), out.date.min(), out.date.max())
    # features of full run for the truncation pairs
    X = ds.prepare("test", col_set="feature", data_key=DataHandlerLP.DK_I)
    random.seed(2025)
    cand = out[out.date >= "2025-01-01"]
    pairs = [cand.iloc[i] for i in random.sample(range(len(cand)), 3)]
    res = []
    for r in pairs:
        o = f"{TMP}/trunc_{r.symbol}_{r.date}.json"
        subprocess.run([PY, os.path.abspath(__file__), "--trunc", r.symbol, r.date, o], check=True)
        t = json.load(open(o))
        fx = X.xs(r.symbol, level="instrument").loc[pd.Timestamp(r.date)]
        tf = pd.Series(t["features"]); a, b = fx.values.astype(float), tf.reindex(fx.index).values.astype(float)
        same = np.allclose(a, b, rtol=1e-5, atol=1e-6, equal_nan=True)
        res.append(dict(symbol=r.symbol, date=r.date, full_score=float(r.score), trunc_score=t["score"],
                        score_diff=abs(float(r.score) - t["score"]), max_feat_absdiff=float(np.nanmax(np.abs(a - b))),
                        n_feat=len(a), features_equal=bool(same)))
    print(pd.DataFrame(res).to_string())
    json.dump(res, open(f"{ROOT}/results/qlib_truncation_test.json", "w"), indent=1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--trunc": main_trunc(*sys.argv[2:5])
    else: main()
