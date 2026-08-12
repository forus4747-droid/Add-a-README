---
name: learning-digest
description: Message the user what got built today, grouped by subject, with a link to each notebook. Step 6 of the Build Your Own Coursera pipeline.
---

# learning-digest

Run from the repo root:

```bash
python scripts/digest.py
```

What it does: finds rows with `built = today`, groups them by topic, and
builds a plain-text message — subject name on its own line, then one line per
item as `Title - https://notebook.google.com/notebook/<notebook_id>`. If any
rows sit at `status=failed`, a final line says "N items failed, check the
error column." Messages over 3,500 characters are split and sent in parts.
Sent via Telegram `sendMessage` with **no parse mode**, so titles with
brackets and underscores cannot break the send. If nothing was built and
nothing failed, nothing is sent.

If Telegram returns an error, the script raises — surface it to the user
rather than failing quietly.

Config needed in `.env`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
`BASEROW_API_TOKEN`, `BASEROW_TABLE_ID`.
