"""Write the final skill's predictions. Usage: run.py START END  (dates inclusive). Uses whatever data is on disk."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lab.data import load_daily, load_5min_long
from final.skill import swing_scores, day_scores
lo, hi = sys.argv[1], sys.argv[2]; tag = sys.argv[3] if len(sys.argv) > 3 else "final"
s = swing_scores(load_daily()); s = s[(s.date >= lo) & (s.date <= hi)]; s.to_parquet(f"results/preds/{tag}_swing.parquet", index=False)
d = day_scores(load_5min_long); d = d[(d.date >= lo) & (d.date <= hi)]; d.to_parquet(f"results/preds/{tag}_day.parquet", index=False)
print("swing rows", len(s), s.date.min(), s.date.max(), "| day rows", len(d), d.date.min(), d.date.max())
