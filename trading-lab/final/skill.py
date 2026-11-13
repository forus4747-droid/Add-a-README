"""THE FINAL SKILL (frozen). Two parameter-free formulas, selected on TRAIN data only by a rule fixed in advance
(results/04_walkforward3.csv, results/04_day_walkforward.csv; reasoning in reports/04_final_skill.md).

swing_scores: for each stock and day t, score = -(rank of 1-day return + rank of 2-day return + rank of 5-day
              return) / 3, ranks taken across all stocks that day. High score = fell most recently = expected to
              do better over the next 5 trading days (open[t+1] -> open[t+6]).
day_scores:   for each Dow stock and day, score = -(rank of the return from the 09:30 open to the 09:55 bar's
              close). High score = weakest first half hour = expected to do better from 10:00 to 15:55.
Nothing is fitted. Inputs for day t are bars dated <= t (swing) or before 10:00 on day t (day)."""
from final.features import build as _build_swing
from final.day_features import build as _build_day

def swing_scores(daily):
    X, _ = _build_swing(daily)
    return X[["symbol", "date"]].assign(score=(-(X.ret1 + X.ret2 + X.ret5) / 3).values)

def day_scores(loader):
    X, _ = _build_day(loader)
    return X[["symbol", "date"]].assign(score=(-X.first30).values)
