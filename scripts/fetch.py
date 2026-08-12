"""Step 3 — learning-fetch: turn every saved link into words on the page.

Processes up to 15 rows with status "new" (oldest first). YouTube links get
a transcript (youtube-transcript-api) plus title/author from oEmbed; other
pages are read through Jina Reader (r.jina.ai — free, no key). Results under
500 characters count as failures. A row is never marked fetched with an
empty transcript.
"""

from __future__ import annotations

import re

import requests

from lib import (
    Library,
    clean_url,
    field_text,
    video_id_from_url,
    STATUS_NEW,
    STATUS_FETCHED,
    STATUS_FAILED,
)

BATCH = 15
MIN_CHARS = 500
URL_RE = re.compile(r"https?://\S+")


def youtube_meta(video_id: str) -> tuple[str, str]:
    """Title and channel name via YouTube oEmbed (no key needed)."""
    try:
        r = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("title", ""), data.get("author_name", "")
    except Exception:
        return "", ""


def youtube_transcript(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi

    try:  # 1.x API
        fetched = YouTubeTranscriptApi().fetch(video_id)
        return " ".join(snippet.text for snippet in fetched)
    except AttributeError:  # pre-1.0 API
        segments = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(seg["text"] for seg in segments)


def read_page(url: str) -> tuple[str, str]:
    """(title, text) for a web page via Jina Reader."""
    r = requests.get(f"https://r.jina.ai/{url}", timeout=90)
    r.raise_for_status()
    text = r.text
    title = ""
    m = re.match(r"Title:\s*(.+)", text)
    if m:
        title = m.group(1).strip()
    return title, text


def main() -> None:
    lib = Library()
    rows = lib.rows_with_status(STATUS_NEW)
    remaining = max(0, len(rows) - BATCH)
    rows = rows[:BATCH]
    if not rows:
        print("Nothing with status 'new'.")
        return

    ok, failed = [], []
    for row in rows:
        raw_url = str(row.get("url") or "")
        # If words surround the link, pull out the first http link and write
        # the cleaned link back.
        m = URL_RE.search(raw_url)
        if not m:
            lib.update_row(row["id"], status=STATUS_FAILED, error="no URL in url field")
            failed.append((raw_url, "no URL in url field"))
            continue
        url = clean_url(m.group(0))
        if url != raw_url:
            lib.update_row(row["id"], url=url)

        try:
            vid = video_id_from_url(url)
            if vid:
                transcript = youtube_transcript(vid)
                title, author = youtube_meta(vid)
                title = title or field_text(row.get("title"))
            else:
                title, transcript = read_page(url)
                author = ""  # byline unknown — do not guess

            if len(transcript.strip()) < MIN_CHARS:
                raise ValueError(
                    f"content too short ({len(transcript.strip())} chars) — "
                    "likely an error page or paywall"
                )

            lib.update_row(
                row["id"],
                title=title or field_text(row.get("title")) or url,
                author=author,
                transcript=transcript,
                status=STATUS_FETCHED,
            )
            ok.append(title or url)
        except Exception as e:
            # note is left alone — that field holds the user's own words
            lib.update_row(row["id"], status=STATUS_FAILED, error=str(e)[:500])
            failed.append((url, str(e)))

    print(f"Fetched {len(ok)} row(s):")
    for t in ok:
        print(f"  - {t}")
    if failed:
        print(f"Failed {len(failed)} row(s):")
        for url, err in failed:
            print(f"  - {url}: {err}")
    if remaining:
        print(f"{remaining} row(s) still queued for the next run.")


if __name__ == "__main__":
    main()
