#!/usr/bin/env bash
# search.sh "term" -- grep transcripts + extracts with context.
#   -t  transcripts only     -e  extracts only     -l  list matching files only
set -uo pipefail
cd "$(dirname "$0")"

DIRS=(transcripts extracts)
MODE=context
while getopts ":tel" opt; do
  case $opt in
    t) DIRS=(transcripts) ;;
    e) DIRS=(extracts) ;;
    l) MODE=list ;;
    *) ;;
  esac
done
shift $((OPTIND - 1))

[ $# -ge 1 ] || { echo "usage: ./search.sh [-t|-e|-l] \"term\""; exit 1; }
TERM_="$*"

if [ "$MODE" = list ]; then
  grep -ril --include='*.md' -- "$TERM_" "${DIRS[@]}" 2>/dev/null | sort
  exit 0
fi

grep -rin --colour=always -C2 --include='*.md' -- "$TERM_" "${DIRS[@]}" 2>/dev/null \
  | sed 's/^/  /'
echo
echo "-- $(grep -ril --include='*.md' -- "$TERM_" "${DIRS[@]}" 2>/dev/null | wc -l | tr -d ' ') file(s) matched for: $TERM_"
