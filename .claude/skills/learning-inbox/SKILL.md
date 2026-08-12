---
name: learning-inbox
description: Pick up links sent to the Telegram bot and add them to the library table, so saves work from the phone. Step 2 of the Build Your Own Coursera pipeline. Telegram discards updates after 24 hours, so run at least daily.
---

# learning-inbox

Run from the repo root:

```bash
python scripts/inbox.py
```

What it does: reads `scripts/learning-offset.txt` (0 if missing), calls
Telegram `getUpdates?offset=<stored+1>`, finds every http(s) link in messages
from the configured chat (text and link entities), de-dupes against URLs
already in the table (after stripping `utm_` params, `si=`, and trailing
slashes), and adds one row per new link with `source=telegram`, `status=new`,
and any extra message text in `note`. The offset is saved only after all rows
were written, so a failed run repeats nothing and loses nothing.

Report how many links were picked up and how many were skipped as duplicates.

Config needed in `.env`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
`BASEROW_API_TOKEN`, `BASEROW_TABLE_ID`.
