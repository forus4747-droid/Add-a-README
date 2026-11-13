"""Truncation test: rebuild features + replay the trade env on data cut at date t; action on t must equal full-run action."""
import sys, os, random; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.argv=sys.argv[:1]
from run import *
raw, _ = build_raw(); full = preprocess(raw)
dates25 = sorted(raw[raw.date >= "2025-01-01"].date.unique()); rng = random.Random(7); picks = sorted(rng.sample(dates25, 3))
out = {}
for k, M in (("ppo", PPO), ("a2c", A2C)):
    m = M.load(f"{MODELDIR}/{k}"); A = np.load(f"{OUT}/finrl_{k}_actions.npy"); _, _, _, _, _ = (None,)*5
    dts = sorted(raw[raw.date >= "2024-01-01"].date.unique())
    for t in picks:
        cut = preprocess(raw[raw.date <= t].copy())
        # features: every row <= t identical between full and truncated pipeline
        f = full[full.date <= t].reset_index(drop=True); c = cut.reset_index(drop=True)
        feat_diff = float(np.abs(f[INDICATORS + ["turbulence", "close"]].values - c[INDICATORS + ["turbulence", "close"]].values).max())
        d, tics, Ac, _, _ = trade(m, cut, "2024-01-01", "2026-01-01")
        assert d[-1] == t, (d[-1], t)
        diff = float(np.abs(Ac[-1] - A[dts.index(t)]).max()); out[f"{k}_{t}"] = dict(max_abs_action_diff=diff, max_abs_feature_diff=feat_diff, days_replayed=len(d))
        print(k, t, out[f"{k}_{t}"], flush=True)
json.dump(out, open(f"{OUT}/finrl_truncation.json", "w"), indent=1)
