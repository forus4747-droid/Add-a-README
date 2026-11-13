"""vC_ew = equal-weight of ranks: v0, 12-1 momentum, low-vol (components chosen after looking at single-signal LOOP results)."""
from skills_long import vC_feat as F
def predict(panel, market):
    W = F.wide(panel); S = F.sigs(W); out = F.combine_ew(S, ["v0", "mom12_1", "lowvol"])
    s = out.where(W["univ"]).stack().rename("score").reset_index(); s.columns = ["date", "symbol", "score"]
    return s[["symbol", "date", "score"]].assign(score=lambda d: d.score.astype(float))
