#!/usr/bin/env bash
# Bring the newest market-monitor code and prediction ledger into this checkout,
# whichever remote branch holds it. Safe to run repeatedly.
#
# Each weekly run commits its ledger to that run's own branch, so the latest state
# may not be on the branch a new session starts from. This finds it and copies it in.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

best_ref=""; best_ts=0; best_branch=""
for b in $(git ls-remote --heads origin | awk '{print $2}' | sed 's#^refs/heads/##'); do
  git fetch -q origin "$b" 2>/dev/null || continue
  ref=$(git rev-parse FETCH_HEAD)
  ts=$(git log -1 --format=%ct "$ref" -- market-monitor/ledger 2>/dev/null)
  ts=${ts:-0}
  if [ "$ts" -gt "$best_ts" ]; then best_ts=$ts; best_ref=$ref; best_branch=$b; fi
done

if [ -z "$best_ref" ]; then
  echo "restore_state: no remote branch holds a ledger; nothing to do"
  exit 0
fi
if git merge-base --is-ancestor "$best_ref" HEAD 2>/dev/null; then
  echo "restore_state: already up to date (newest ledger is on $best_branch)"
  exit 0
fi
git checkout -q "$best_ref" -- market-monitor
echo "restore_state: restored market-monitor from $best_branch ($(git log -1 --format=%cI "$best_ref"))"
