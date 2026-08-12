"""Step 6 — learning-digest: get told what landed.

Sends a Telegram message listing everything built today, grouped by subject,
with a link to each notebook. Sends nothing if nothing was built and nothing
failed. No parse mode is set, so titles with brackets or underscores cannot
break the send.
"""

from __future__ import annotations

import requests

from lib import Library, field_text, require, today, STATUS_FAILED

MAX_LEN = 3500
NOTEBOOK_URL = "https://notebook.google.com/notebook/"


def send(token: str, chat_id: str, text: str) -> None:
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},  # deliberately no parse_mode
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Telegram error {r.status_code}: {r.text[:300]}")


def split_message(text: str) -> list[str]:
    if len(text) <= MAX_LEN:
        return [text]
    parts, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > MAX_LEN and current:
            parts.append(current)
            current = ""
        current += line
    if current:
        parts.append(current)
    return parts


def main() -> None:
    token = require("TELEGRAM_BOT_TOKEN")
    chat_id = require("TELEGRAM_CHAT_ID")
    lib = Library()

    rows = lib.all_rows()
    built_today = [r for r in rows if str(r.get("built") or "") == today()]
    failed_count = sum(1 for r in rows if field_text(r.get("status")) == STATUS_FAILED)

    if not built_today and failed_count == 0:
        print("Nothing built today and nothing failed — no digest sent.")
        return

    by_topic: dict[str, list[dict]] = {}
    for row in built_today:
        by_topic.setdefault(field_text(row.get("topic")) or "Unsorted", []).append(row)

    lines = []
    for topic in sorted(by_topic):
        lines.append(topic)
        for row in by_topic[topic]:
            title = field_text(row.get("title")) or str(row.get("url") or "")
            lines.append(f"{title} - {NOTEBOOK_URL}{field_text(row.get('notebook_id'))}")
        lines.append("")
    if failed_count:
        lines.append(f"{failed_count} items failed, check the error column.")

    message = "\n".join(lines).strip()
    for part in split_message(message):
        send(token, chat_id, part)
    print(f"Digest sent ({len(built_today)} item(s), {failed_count} failed).")


if __name__ == "__main__":
    main()
