---
name: learning-fetch
description: Read everything saved but not yet read, storing full text in the library table so the rest of the pipeline has something to work from. Step 3 of the Build Your Own Coursera pipeline.
---

# learning-fetch

Run from the repo root:

```bash
python scripts/fetch.py
```

What it does: takes up to 15 rows with `status=new` (oldest first). YouTube
links get a transcript via youtube-transcript-api plus title/channel from
oEmbed; anything else is read as text through Jina Reader (`r.jina.ai`, free,
no key). On success it writes `title`, `author` (never guessed — left empty
when unknown), `transcript`, and `status=fetched`. Results under 500
characters, timeouts, and errors are treated as failures: `status=failed`
with a one-line `error`, and the user's `note` field is left alone. A row is
never marked fetched with an empty transcript.

Report which rows worked, which failed and why, and how many are still queued.

To swap reading tools, edit `youtube_transcript()` / `read_page()` in
`scripts/fetch.py` — alternatives with free tiers: Firecrawl, Exa, Supadata,
Jina Reader, Apify.
