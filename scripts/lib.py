"""Shared plumbing for the Build Your Own Coursera pipeline.

Loads configuration from .env / environment variables and talks to the
Baserow "Library" table (the one table everything lands in — see README).
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

# Status ladder: new -> fetched -> sorted -> done  (failed = parked with a reason)
STATUS_NEW = "new"
STATUS_FETCHED = "fetched"
STATUS_SORTED = "sorted"
STATUS_DONE = "done"
STATUS_FAILED = "failed"


def load_env() -> None:
    """Load KEY=VALUE pairs from .env at the repo root (without overriding
    variables already set in the environment)."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def require(name: str) -> str:
    load_env()
    value = os.environ.get(name)
    if not value:
        sys.exit(
            f"Missing required setting {name}. Copy .env.example to .env and fill it in."
        )
    return value


def today() -> str:
    return date.today().isoformat()


def clean_url(url: str) -> str:
    """Normalize a URL for de-duplication: strip utm_* params, any si= param,
    and a trailing slash — per step 2 of the guide."""
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() != "si"
    ]
    path = parts.path.rstrip("/") or parts.path
    return urlunsplit((parts.scheme, parts.netloc, path, urlencode(query), ""))


def video_id_from_url(url: str) -> str | None:
    """Extract a YouTube video ID: the v= value, or the last path segment for
    youtu.be / /shorts/ links, dropping everything after & or ?."""
    from urllib.parse import urlsplit, parse_qs

    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    if host not in ("youtube.com", "youtu.be", "m.youtube.com", "music.youtube.com"):
        return None
    if host == "youtu.be":
        vid = parts.path.strip("/").split("/")[0]
    elif parts.path.startswith("/shorts/") or parts.path.startswith("/live/"):
        vid = parts.path.split("/")[2] if len(parts.path.split("/")) > 2 else ""
    else:
        vid = (parse_qs(parts.query).get("v") or [""])[0]
    vid = vid.split("&")[0].split("?")[0]
    return vid or None


class Library:
    """Thin client for the Baserow Library table (REST API, user field names)."""

    def __init__(self) -> None:
        self.base = require("BASEROW_API_URL").rstrip("/")
        self.table_id = require("BASEROW_TABLE_ID")
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Token {require('BASEROW_API_TOKEN')}"

    def _rows_url(self) -> str:
        return f"{self.base}/api/database/rows/table/{self.table_id}/"

    def all_rows(self) -> list[dict]:
        rows, page = [], 1
        while True:
            r = self.session.get(
                self._rows_url(),
                params={"user_field_names": "true", "size": 200, "page": page},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            rows.extend(data["results"])
            if not data.get("next"):
                return rows
            page += 1

    def rows_with_status(self, status: str, limit: int | None = None) -> list[dict]:
        rows = [r for r in self.all_rows() if field_text(r.get("status")) == status]
        rows.sort(key=lambda r: (r.get("added") or "", r["id"]))
        return rows[:limit] if limit else rows

    def add_row(self, **fields) -> dict:
        r = self.session.post(
            self._rows_url(), params={"user_field_names": "true"}, json=fields, timeout=30
        )
        r.raise_for_status()
        return r.json()

    def update_row(self, row_id: int, **fields) -> dict:
        r = self.session.patch(
            f"{self._rows_url()}{row_id}/",
            params={"user_field_names": "true"},
            json=fields,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


def field_text(value) -> str:
    """Baserow single-select fields come back as {'id':..,'value':..}; text
    fields as plain strings. Normalize either to a string."""
    if isinstance(value, dict):
        return str(value.get("value") or "")
    return str(value or "")
