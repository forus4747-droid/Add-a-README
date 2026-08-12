"""Step 2 — learning-inbox: pick up links texted to the Telegram bot.

Reads new updates from the bot via getUpdates (offset-based, so nothing
repeats), extracts links from your own messages, and adds each new link
as a row with source "telegram". The offset is only saved after every row
was written successfully.
"""

from __future__ import annotations

import re
from pathlib import Path

import requests

from lib import Library, clean_url, require, today, STATUS_NEW

OFFSET_FILE = Path(__file__).resolve().parent / "learning-offset.txt"
URL_RE = re.compile(r"https?://\S+")


def read_offset() -> int:
    try:
        return int(OFFSET_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def links_in_message(msg: dict) -> list[str]:
    text = msg.get("text") or msg.get("caption") or ""
    links = URL_RE.findall(text)
    # Also read link entities (text_link carries the URL in the entity itself)
    for ent in (msg.get("entities") or []) + (msg.get("caption_entities") or []):
        if ent.get("type") == "text_link" and ent.get("url"):
            links.append(ent["url"])
        elif ent.get("type") == "url":
            start, length = ent.get("offset", 0), ent.get("length", 0)
            links.append(text[start : start + length])
    # De-dupe while preserving order
    seen, out = set(), []
    for link in links:
        link = link.rstrip(").,]")
        if link not in seen:
            seen.add(link)
            out.append(link)
    return out


def main() -> None:
    token = require("TELEGRAM_BOT_TOKEN")
    chat_id = str(require("TELEGRAM_CHAT_ID"))
    lib = Library()

    stored = read_offset()
    r = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        params={"offset": stored + 1},
        timeout=30,
    )
    r.raise_for_status()
    updates = r.json().get("result", [])
    if not updates:
        print("No new Telegram messages.")
        return

    existing = {clean_url(str(row.get("url") or "")) for row in lib.all_rows()}

    added = skipped = 0
    max_update_id = stored
    for update in updates:
        max_update_id = max(max_update_id, update.get("update_id", 0))
        msg = update.get("message") or update.get("channel_post") or {}
        if str((msg.get("chat") or {}).get("id", "")) != chat_id:
            continue
        links = links_in_message(msg)
        if not links:
            continue  # ignore messages with no link in them
        text = msg.get("text") or msg.get("caption") or ""
        note = URL_RE.sub("", text).strip()
        for link in links:
            cleaned = clean_url(link)
            if cleaned in existing:
                skipped += 1
                continue
            lib.add_row(
                url=cleaned,
                source="telegram",
                status=STATUS_NEW,
                added=today(),
                note=note,
            )
            existing.add(cleaned)
            added += 1

    # Only saved after every row was written; on an exception above we never
    # get here, so nothing is confirmed and the next run retries.
    OFFSET_FILE.write_text(str(max_update_id))
    print(f"Picked up {added} link(s), skipped {skipped} duplicate(s).")


if __name__ == "__main__":
    main()
