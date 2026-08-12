"""Step 4 — learning-sort: group the similar things together.

Assigns each fetched row a subject (topic) so step 5 can file related
material into the same notebook. Classification runs on the Claude API
(set ANTHROPIC_API_KEY in .env); rows whose transcript is too thin to
judge are filed under "Unsorted" rather than guessed at.
"""

from __future__ import annotations

import json
import re

from lib import Library, field_text, load_env, STATUS_FETCHED, STATUS_SORTED

BATCH = 25
NAME_RE = re.compile(r"^[A-Za-z ]{1,30}$")

SCHEMA = {
    "type": "object",
    "properties": {
        "assignments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "row_id": {"type": "integer"},
                    "topic": {"type": "string"},
                },
                "required": ["row_id", "topic"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["assignments"],
    "additionalProperties": False,
}

PROMPT = """You are sorting saved learning material into subjects.

Existing subjects already in use (reuse these names EXACTLY — same capitals,
same singular/plural — whenever an item fits one):
{topics}

Rules:
- Only invent a new subject if none of the existing ones fit.
- New names are one or two plain words in Title Case, letters and spaces only,
  under 30 characters (e.g. AI Agents, Sales, Distribution, Finance).
- Once you invent a subject in this batch, reuse it for later items in the
  batch instead of inventing a near-copy.
- Before inventing, check the name is not an existing subject with different
  capitals, an s on the end, or an abbreviation.
- If an item's text is empty or too thin to judge, use the subject "Unsorted".

Items to sort (row_id, title, then the first ~2000 words of the text):

{items}

Return one assignment per item."""


def main() -> None:
    load_env()
    import anthropic

    lib = Library()
    rows = lib.rows_with_status(STATUS_FETCHED, limit=BATCH)
    if not rows:
        print("Nothing with status 'fetched'.")
        return

    existing_topics = sorted(
        {field_text(r.get("topic")) for r in lib.all_rows() if field_text(r.get("topic"))}
    )

    items = []
    for row in rows:
        excerpt = " ".join(field_text(row.get("transcript")).split()[:2000])
        items.append(
            f"row_id: {row['id']}\ntitle: {field_text(row.get('title'))}\ntext: {excerpt}\n"
        )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=16000,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(
                    topics="\n".join(f"- {t}" for t in existing_topics) or "(none yet)",
                    items="\n---\n".join(items),
                ),
            }
        ],
    )
    if response.stop_reason == "refusal":
        raise SystemExit("Classification request was refused; nothing was sorted.")
    data = json.loads(next(b.text for b in response.content if b.type == "text"))

    by_id = {row["id"]: row for row in rows}
    new_topics = []
    for a in data["assignments"]:
        row = by_id.get(a["row_id"])
        topic = a["topic"].strip()
        if row is None or not topic:
            continue
        if not NAME_RE.match(topic):
            topic = "Unsorted"
        if topic not in existing_topics and topic not in new_topics and topic != "Unsorted":
            new_topics.append(topic)
        lib.update_row(row["id"], topic=topic, status=STATUS_SORTED)
        print(f"  {field_text(row.get('title'))!r} -> {topic}")

    if new_topics:
        print("New subjects created (rename now rather than later if they drift):")
        for t in new_topics:
            print(f"  - {t}")


if __name__ == "__main__":
    main()
