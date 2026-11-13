"""vA = no improvement found: identical in content to v0 (equal-weight rank of -r1,-r2,-r5), wide-matrix implementation.
Variants V1-V8 (beta-adjusted, vol-scaled, overnight/intraday, volume-conditioned, vol-tilt) are in vA_dev.py; none beat v0 on 2006-2012."""
from skills_long.vA_feat import build, xrank, to_long
def predict(panel, market):
    W, U = build(panel, market)
    return to_long(-(xrank(W["r1"], U) + xrank(W["r2"], U) + xrank(W["r5"], U)) / 3, U).dropna()
