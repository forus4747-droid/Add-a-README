import numpy as np, pandas as pd
from skills_long.vA_feat import build, xrank

def variants(panel, market):
    W, U = build(panel, market)
    X = lambda k, M=None: xrank(W[k] if M is None else M, U)
    out = {}
    out["v0"] = -(X("r1") + X("r2") + X("r5")) / 3
    E = {k: W["r" + k] - W["beta"].fillna(1) * W["mkt" + k] for k in "125"}
    out["V1_beta"] = -sum(X(0, E[k]) for k in "125") / 3
    Z = {k: W["r" + k] / (W["vol"] * np.sqrt(int(k))) for k in "125"}
    out["V2_volscaled"] = -sum(X(0, Z[k]) for k in "125") / 3
    EZ = {k: E[k] / (W["vol"] * np.sqrt(int(k))) for k in "125"}
    out["V3_beta_vol"] = -sum(X(0, EZ[k]) for k in "125") / 3
    out["V4_on_id"] = -(X("on1") + X("id1") + X("r2") + X("r5")) / 4
    vrr = X("vr") + 0.5
    out["V5_vol_cond"] = out["v0"] * (1.5 - vrr)
    out["V5b_vol_cond_up"] = out["v0"] * (0.5 + vrr)
    out["V6_beta_vol_x_volcond"] = out["V3_beta_vol"] * (1.5 - vrr)
    out["V6b"] = out["V3_beta_vol"] * (0.5 + vrr)
    base = out["v0"]
    out["V7_tail_cubic"] = -((4 * (-base)) ** 3)
    out["V8_vol_tilt"] = base * (0.5 + (X("vol") + 0.5))
    return W, U, out
