"""Proof check for the engine test. Usage: compare_trades.py ENGINE S1|S2
Compares results/trades/{ENGINE}_{S}.csv with results/trades/reference_{S}.csv and writes
results/compare_{ENGINE}_{S}.json. PASS = same trades, same timestamps, |pnl diff| <= $0.01 each."""
import sys, json, pandas as pd
eng, s = sys.argv[1], sys.argv[2]
K = ["symbol", "entry_time"]
r = pd.read_csv(f"results/trades/reference_{s}.csv"); e = pd.read_csv(f"results/trades/{eng}_{s}.csv")
for c in ("entry_time", "exit_time"): e[c] = e[c].astype(str).str[:16 if s == "S1" else 10]
m = r.merge(e, on=K, how="outer", suffixes=("_ref", "_eng"), indicator=True)
both = m[m._merge == "both"]
out = dict(engine=eng, strategy=s, ref_trades=len(r), engine_trades=len(e),
    missing_in_engine=int((m._merge == "left_only").sum()), extra_in_engine=int((m._merge == "right_only").sum()),
    exit_time_mismatch=int((both.exit_time_ref != both.exit_time_eng).sum()),
    entry_price_mismatch=int(((both.entry_price_ref - both.entry_price_eng).abs() > 1e-6).sum()),
    exit_price_mismatch=int(((both.exit_price_ref - both.exit_price_eng).abs() > 1e-6).sum()),
    shares_mismatch=int((both.shares_ref != both.shares_eng).sum()),
    pnl_mismatch_over_1c=int(((both.pnl_net_ref - both.pnl_net_eng).abs() > 0.01).sum()),
    max_abs_pnl_diff=float((both.pnl_net_ref - both.pnl_net_eng).abs().max()) if len(both) else None,
    ref_total_pnl=round(float(r.pnl_net.sum()), 2), engine_total_pnl=round(float(e.pnl_net.sum()), 2))
out["PASS"] = all(out[k] == 0 for k in out if k.endswith("mismatch") or k.endswith("_engine") or k.endswith("1c")) and len(e) == len(r)
json.dump(out, open(f"results/compare_{eng}_{s}.json", "w"), indent=1); print(json.dumps(out, indent=1))
bad = m[(m._merge != "both")].head(10)
if len(bad): print("first unmatched trades:\n", bad[K + ["_merge"]].to_string(index=False))
