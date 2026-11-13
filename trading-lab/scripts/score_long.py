"""Phase 2 scorer. Usage: score_long.py VERSION TIER [return|abs] [--diagnose] [--causal]
TIER: LOOP (1991-2012) | CONFIRM (2013-2019) | LOCKBOX (2020-2026). CONFIRM/LOCKBOX need LAB_LONG pointing at the full data.
Writes results/P2_{VERSION}_{TIER}_{kind}.csv (per-year) and prints the pooled summary."""
import sys, os, json, importlib; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, warnings; warnings.filterwarnings("ignore")
from lab import long as L
ver, tier = sys.argv[1], sys.argv[2]; kind = next((a for a in sys.argv[3:] if a in ("return", "abs")), "return")
W = {"LOOP": ("1991-01-01", "2012-12-31"), "CONFIRM": ("2013-01-01", "2019-12-31"), "LOCKBOX": ("2020-01-01", "2026-12-31")}[tier]
panel, market = L.load_panel(), L.load_market()
assert tier == "LOOP" or panel.date.max() > "2013", "this data root has no data after 2012"
mod = importlib.import_module(f"skills_long.{ver}"); fn = getattr(mod, "predict_abs" if kind == "abs" else "predict")
preds = fn(panel, market); T = L.targets(panel, kind)
y, s = L.score(preds, T, *W); y.to_csv(f"results/P2_{ver}_{tier}_{kind}.csv"); json.dump(s, open(f"results/P2_{ver}_{tier}_{kind}.json", "w"), indent=1)
print(y.to_string()); print(json.dumps(s))
if "--diagnose" in sys.argv:
    for k, v in L.diagnose(preds, panel, market, *W, kind=kind).items(): print("\n" + k); print(v.to_string())
if "--causal" in sys.argv: print("causal check:", L.check_causal(fn, panel, market))
