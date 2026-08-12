"""Step 5 — learning-build: build the study guide, briefing doc and quiz.

Runs on your own computer using the notebooklm-py CLI (Setup 4 in the
guide: `pip install "notebooklm-py[browser]>=0.8.0"` then `notebooklm login`).
Groups sorted rows by topic, creates/reuses one notebook per topic, adds
each row's URL as a source, then generates a study guide, briefing doc and
quiz. Rows are only marked done if all three pieces generated.
"""

from __future__ import annotations

import json
import subprocess
import sys

from lib import Library, field_text, today, STATUS_SORTED, STATUS_DONE

BATCH = 20


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["notebooklm", *args], capture_output=True, text=True, check=check, timeout=1800
    )


def preflight() -> None:
    """Do not invent commands: verify the CLI exists and auth works, or stop."""
    try:
        run("--help")
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        sys.exit(f"notebooklm CLI is not available ({e}). Run Setup 4 first.")
    try:
        run("auth", "check", "--test", "--json")
    except subprocess.CalledProcessError as e:
        sys.exit(f"notebooklm auth check failed:\n{e.stderr}\nRun `notebooklm login`.")


def list_notebooks() -> dict[str, str]:
    out = run("list", "--json").stdout
    notebooks = json.loads(out)
    if isinstance(notebooks, dict):
        notebooks = notebooks.get("notebooks", [])
    return {nb.get("title") or nb.get("name"): nb.get("id") for nb in notebooks}


def notebook_sources(notebook_id: str) -> set[str]:
    try:
        out = run("source", "list", "--json", "-n", notebook_id).stdout
        sources = json.loads(out)
        if isinstance(sources, dict):
            sources = sources.get("sources", [])
        return {s.get("url", "") for s in sources if isinstance(s, dict)}
    except Exception:
        return set()  # can't list — fall back to per-run tracking only


def main() -> None:
    preflight()
    lib = Library()

    rows = [
        r
        for r in lib.rows_with_status(STATUS_SORTED, limit=BATCH)
        if field_text(r.get("topic")) and field_text(r.get("topic")) != "Unsorted"
    ]
    if not rows:
        print("Nothing with status 'sorted' and a topic.")
        return

    by_topic: dict[str, list[dict]] = {}
    for row in rows:
        by_topic.setdefault(field_text(row.get("topic")), []).append(row)

    notebooks = list_notebooks()
    created, updated = [], []

    for topic, topic_rows in by_topic.items():
        try:
            if topic in notebooks:
                nb_id = notebooks[topic]
                updated.append(topic)
            else:
                out = run("create", topic).stdout
                try:
                    nb_id = json.loads(out).get("id") or out.strip()
                except json.JSONDecodeError:
                    nb_id = out.strip().split()[-1]
                notebooks[topic] = nb_id
                created.append(topic)

            existing = notebook_sources(nb_id)
            added_rows = []
            for row in topic_rows:
                url = str(row.get("url") or "")
                try:
                    if url not in existing:  # never add the same url twice
                        run("source", "add", url, "-n", nb_id)
                        existing.add(url)
                    added_rows.append(row)
                except subprocess.CalledProcessError as e:
                    lib.update_row(row["id"], error=f"source add failed: {e.stderr[:400]}")

            if not added_rows:
                continue

            run("generate", "report", "--format", "study-guide", "-n", nb_id)
            run("generate", "report", "--format", "briefing-doc", "-n", nb_id)
            run("generate", "quiz", "-n", nb_id)

            # Only mark done once all three pieces of material generated.
            for row in added_rows:
                lib.update_row(
                    row["id"], notebook_id=nb_id, built=today(), status=STATUS_DONE
                )
            print(f"Built study guide, briefing doc and quiz for '{topic}' "
                  f"({len(added_rows)} source(s)).")
        except subprocess.CalledProcessError as e:
            # Leave the rows at sorted, record why, carry on with other topics.
            for row in topic_rows:
                lib.update_row(row["id"], error=f"build failed: {e.stderr[:400]}")
            print(f"Topic '{topic}' failed: {e.stderr.strip()[:200]}")

    if created:
        print(f"Created notebook(s): {', '.join(created)}")
    if updated:
        print(f"Added to existing notebook(s): {', '.join(updated)}")


if __name__ == "__main__":
    main()
