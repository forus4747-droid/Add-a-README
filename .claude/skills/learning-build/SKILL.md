---
name: learning-build
description: Turn everything saved into real course material (study guide, briefing doc, quiz) filed under the right subject in Gemini Notebook. Step 5 of the Build Your Own Coursera pipeline. Must run on the user's own computer.
---

# learning-build

Run from the repo root, **on the user's own machine** (Setup 4 must be done:
`pip install "notebooklm-py[browser]>=0.8.0"`, `notebooklm login`):

```bash
python scripts/build.py
```

The script first runs `notebooklm --help` and `notebooklm auth check --test
--json`; if either fails it stops — do not invent commands, tell the user to
complete Setup 4.

What it does: takes up to 20 rows with `status=sorted` and a non-empty topic,
groups them by topic, reuses a notebook whose name matches the topic exactly
(else `notebooklm create "TOPIC"`), adds each row's URL as a source (never
adding the same URL to a notebook twice — existing sources are checked
first), then generates a study guide, briefing doc and quiz once per
notebook. Only rows whose notebook got all three pieces are marked
`status=done` with `notebook_id` and `built=today`. Failures leave the row
at `sorted` with the reason in `error`, and other topics carry on.

Report which notebooks were created, which were added to, and what was built.
If Google changes something and the unofficial tool breaks, steps 1–4 keep
working — sources can be added by hand until it's patched.
