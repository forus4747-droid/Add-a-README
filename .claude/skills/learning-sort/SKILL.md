---
name: learning-sort
description: Decide which subject each fetched item belongs to so related material lands in the same notebook. Step 4 of the Build Your Own Coursera pipeline. Worth checking by hand for the first week.
---

# learning-sort

Run from the repo root:

```bash
python scripts/sort.py
```

What it does: takes up to 25 rows with `status=fetched` (oldest first), reads
the subjects already in use across the whole table, and classifies each row
from its title and the first ~2000 words of transcript using the Claude API
(`ANTHROPIC_API_KEY` in `.env`). Rules enforced: reuse existing subject names
spelled exactly as they appear; only invent a new subject when nothing fits
(one or two plain Title Case words, letters and spaces only, under 30 chars);
thin/empty transcripts go to `Unsorted` rather than being guessed. Each sorted
row gets `topic` written and `status=sorted`.

Show the user every row sorted with its subject, and list any newly created
subjects so they can rename them now rather than later (subject names become
notebook names in step 5, and renaming later is a chore). Warn if two
near-identical buckets appear (e.g. "AI Agent" vs "AI Agents").

If no `ANTHROPIC_API_KEY` is configured, do the classification yourself:
follow the same rules, then write each row back with the Baserow API using
the helpers in `scripts/lib.py`.
