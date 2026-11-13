"""vC = walk-forward IC-weighted blend of v0 (reversal) with slower signals (12-1 momentum, low-vol, 52w-high, event drift).
Weights for year Y = clipped-at-zero expanding mean daily rank IC using only labels known before Y-01-01; 1991-93 use v0 alone."""
import numpy as np, pandas as pd
from skills_long import vC_feat as F
NAMES = ["v0", "mom12_1", "lowvol", "hi52", "event"]
def predict(panel, market):
    W = F.wide(panel); S = F.sigs(W); out, _ = F.combine_wf(S, W, NAMES)
    s = out.where(W["univ"]).stack().rename("score").reset_index(); s.columns = ["date", "symbol", "score"]
    return s[["symbol", "date", "score"]].assign(score=lambda d: d.score.astype(float))
