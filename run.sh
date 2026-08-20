#!/usr/bin/env bash
# yt-kb — build the transcript knowledge base. Idempotent: re-running only
# processes new/pending items. Subtitles only; never downloads video or audio.
set -euo pipefail
cd "$(dirname "$0")"

LIMIT="${LIMIT:-150}"     # max videos to fetch per run (politeness)
SLEEP="${SLEEP:-2}"       # seconds between requests

command -v yt-dlp >/dev/null 2>&1 || {
  echo "yt-dlp not found. Install:  pip install -U yt-dlp"; exit 1; }
echo "yt-dlp $(yt-dlp --version)"

echo "== 1/4 discover =="
python3 pipeline.py discover

echo "== 2/4 fetch subtitles =="
python3 pipeline.py fetch --limit "$LIMIT" --sleep "$SLEEP"

echo "== 3/4 clean =="
python3 pipeline.py clean

echo "== 4/4 report =="
python3 pipeline.py report

cat <<'NOTE'

Next: write one extract per transcript into extracts/<channel>/<title>.md
(Track A or Track B template -- see README.md section "Step 4"), then refresh
KNOWLEDGE.md / OPERATORS.md / INDEX.md / QUESTIONS.md.
NOTE
