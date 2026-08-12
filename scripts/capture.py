"""Step 1 — learning-capture: watch the Learn playlist.

Reads the YouTube playlist RSS feed and adds any video not already in the
library table as a new row with status "new".
"""

from __future__ import annotations

import html
import sys
import time
import xml.etree.ElementTree as ET

import requests

from lib import Library, require, today, video_id_from_url, STATUS_NEW

ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"

FEED_URL = "https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"


def fetch_feed(playlist_id: str) -> list[tuple[str, str]]:
    """Return [(video_id, title), ...] from the playlist feed.
    Retries once after 10 seconds on error or an empty feed, then gives up."""
    url = FEED_URL.format(playlist_id=playlist_id)
    for attempt in (1, 2):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            entries = []
            for entry in root.findall(f"{ATOM}entry"):
                vid = entry.findtext(f"{YT}videoId")
                # The feed-level <title> is the playlist name; only read the
                # <title> inside each <entry>.
                title = entry.findtext(f"{ATOM}title") or ""
                if vid:
                    entries.append((vid, html.unescape(title)))
            if entries:
                return entries
            raise ValueError("feed returned no entries")
        except Exception as e:
            if attempt == 1:
                print(f"Feed fetch failed ({e}); retrying in 10s...")
                time.sleep(10)
            else:
                sys.exit(f"Playlist feed failed twice ({e}). Nothing was added.")
    return []


def main() -> None:
    playlist_id = require("YT_PLAYLIST_ID")
    lib = Library()

    entries = fetch_feed(playlist_id)

    # Match on video ID only — never on published date (the feed's date is
    # when the video went up, not when it was saved).
    known_ids = set()
    for row in lib.all_rows():
        vid = video_id_from_url(str(row.get("url") or ""))
        if vid:
            known_ids.add(vid)

    added = []
    for vid, title in entries:
        if vid in known_ids:
            continue
        lib.add_row(
            url=f"https://www.youtube.com/watch?v={vid}",
            source="youtube",
            title=title,
            status=STATUS_NEW,
            added=today(),
        )
        known_ids.add(vid)
        added.append(title)

    if added:
        print(f"Added {len(added)} row(s):")
        for title in added:
            print(f"  - {title}")
    else:
        print("All feed entries were already in the table.")
    if len(entries) == 15 and not added:
        print(
            "Warning: the feed only shows the newest 15 saves. If you've saved "
            "more than 15 things since the last run, some may have been missed."
        )


if __name__ == "__main__":
    main()
