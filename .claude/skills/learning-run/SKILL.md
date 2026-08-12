---
name: learning-run
description: Run the whole Build Your Own Coursera pipeline once, in order - capture, inbox, fetch, sort, build, digest - each step finishing before the next starts. Step 7 wires this to a daily 6am schedule.
---

# learning-run

Run from the repo root:

```bash
python scripts/run_all.py
```

Runs all six steps in exactly this order, each finishing before the next
starts:

1. `learning-capture` — watch the playlist
2. `learning-inbox` — pick up Telegram links
3. `learning-fetch` — get the actual text
4. `learning-sort` — group into subjects
5. `learning-build` — build NotebookLM material (needs the user's own machine)
6. `learning-digest` — send the Telegram summary

A failing step stops the run; broken rows park at `status=failed` with the
reason in `error`, so nothing silently blocks the queue. Show the user what
each step did.

You can also run a subset: `python scripts/run_all.py capture inbox fetch`.

To schedule the daily 6am run, see "Set it running" in the README (cron on
the user's own machine, since step 5 must run there).
