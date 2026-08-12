---
name: learning-capture
description: Check the YouTube Learn playlist and add any saved-but-unprocessed video as a new row in the library table. Step 1 of the Build Your Own Coursera pipeline.
---

# learning-capture

Run from the repo root:

```bash
python scripts/capture.py
```

What it does: fetches the Learn playlist RSS feed (up to 15 entries), extracts
each entry's video ID and title, compares against video IDs already in the
library table (matching on video ID only, never the published date), and adds
one row per new video with `source=youtube`, `status=new`, `added=today`.

Report back to the user how many rows were added and their titles. If the
script warns that all 15 entries were already present, pass on the warning
that saves beyond the 15-item feed window may have been missed.

If the feed fails twice (the script retries once after 10s), nothing is added —
tell the user and stop.

Config needed in `.env`: `YT_PLAYLIST_ID`, `BASEROW_API_TOKEN`, `BASEROW_TABLE_ID`.
