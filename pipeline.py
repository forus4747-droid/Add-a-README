#!/usr/bin/env python3
"""
yt-kb pipeline — Canadian Business Acquisition YouTube knowledge base.

Subtitles only. Never downloads video or audio.

Commands
    discover   list candidate videos from sources.json -> manifest.csv (pending)
    fetch      download subtitles for pending rows -> raw/{channel}/{id}.vtt
    clean      convert raw subs -> transcripts/{channel}/{safe_title}.md
    ingest     import transcripts fetched out-of-band (MCP/manual) from raw/_inbox
    status     one-line counts
    report     step 6 summary report

Stdlib only. yt-dlp is shelled out to, not imported.
"""

import argparse
import csv
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "manifest.csv")
SOURCES = os.path.join(ROOT, "sources.json")
RAW = os.path.join(ROOT, "raw")
INBOX = os.path.join(RAW, "_inbox")
TRANSCRIPTS = os.path.join(ROOT, "transcripts")
EXTRACTS = os.path.join(ROOT, "extracts")

FIELDS = [
    "video_id", "channel", "title", "duration", "url",
    "tier", "track", "status", "downloaded_at", "transcript", "extract", "notes",
]

# status values
PENDING, DONE, NO_SUBS, SKIPPED, ERROR = "pending", "done", "no_subs", "skipped", "error"

# Long-form only: clips shorter than this are excluded from the knowledge base.
# Short videos carry headlines; the unit economics live in the long ones.
LONG_FORM_MIN = 600  # seconds (10:00)


# ---------------------------------------------------------------- utilities

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_title(title, maxlen=90):
    """Filesystem-safe slug that a human can still read in a file listing."""
    t = html.unescape(title or "untitled")
    t = re.sub(r"[^\w\s\-\.]", " ", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace(" ", "-")
    t = re.sub(r"-{2,}", "-", t).strip("-.")
    return (t[:maxlen].rstrip("-.") or "untitled")


def safe_channel(name):
    return safe_title(name, maxlen=60)


def hms(seconds):
    try:
        s = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- manifest

def load_manifest():
    if not os.path.exists(MANIFEST):
        return []
    with open(MANIFEST, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for f in FIELDS:
            r.setdefault(f, "")
    return rows


def save_manifest(rows):
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({f: r.get(f, "") for f in FIELDS})
    os.replace(tmp, MANIFEST)


def index_by_id(rows):
    return {r["video_id"]: r for r in rows if r.get("video_id")}


# ---------------------------------------------------------------- filtering

def matches_keywords(title, include, exclude):
    """include=[] means 'no include filter'. Matching is case-insensitive substring."""
    t = (title or "").lower()
    if exclude and any(k.lower() in t for k in exclude):
        return False
    if include and not any(k.lower() in t for k in include):
        return False
    return True


PROMO_PAT = re.compile(r"\b(course|webinar replay|join now|free training|masterclass sign)\b", re.I)


def keep_video(vid, src):
    """Apply spec section 3/6 filters. Returns (keep: bool, reason: str)."""
    title = vid.get("title") or ""
    dur = vid.get("duration")

    if vid.get("is_short") or "/shorts/" in (vid.get("url") or ""):
        return False, "short"

    try:
        dur = float(dur)
    except (TypeError, ValueError):
        # unknown duration (live/premiere placeholder) -> skip, cheaper than a bad fetch
        return False, "no-duration"

    min_dur = src.get("min_duration", LONG_FORM_MIN)
    if dur < min_dur:
        return False, f"too-short({int(dur)}s<{min_dur}s)"

    max_dur = src.get("max_duration", 7200)
    if dur > max_dur and int(src.get("tier", 3)) != 1:
        return False, f"too-long({int(dur)}s)"

    if PROMO_PAT.search(title) and not src.get("allow_promo"):
        return False, "promo"

    if not matches_keywords(title, src.get("include", []), src.get("exclude", [])):
        return False, "keyword"

    return True, ""


# ---------------------------------------------------------------- discovery

def ytdlp_available():
    return shutil.which("yt-dlp") is not None


def run_ytdlp(args, timeout=300):
    cmd = ["yt-dlp"] + args
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"
    return p.returncode, p.stdout, p.stderr


def discover_source(src, limit):
    """Return list of video dicts from one source entry."""
    stype = src.get("type", "channel")
    if stype == "search":
        target = f"ytsearch{src.get('max_results', 15)}:{src['query']}"
    else:
        target = src["url"]

    args = [
        "--flat-playlist", "--ignore-errors", "--no-warnings",
        "--print", "%(id)s\t%(title)s\t%(duration)s\t%(webpage_url)s",
    ]
    if stype != "search" and src.get("max_results"):
        args += ["--playlist-end", str(src["max_results"])]
    args.append(target)

    code, out, err = run_ytdlp(args, timeout=src.get("timeout", 600))
    if code != 0 and not out.strip():
        log(f"    ! yt-dlp failed for {src['name']}: {err.strip().splitlines()[-1] if err.strip() else code}")
        return []

    vids = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        vid_id, title, dur, url = parts[0], parts[1], parts[2], parts[3]
        if not vid_id or vid_id == "NA":
            continue
        vids.append({
            "id": vid_id,
            "title": title,
            "duration": None if dur in ("NA", "None", "") else dur,
            "url": url,
        })
    return vids[:limit] if limit else vids


def cmd_discover(args):
    if not ytdlp_available():
        log("yt-dlp not found. Install with: pip install -U yt-dlp")
        return 1
    with open(SOURCES, encoding="utf-8") as fh:
        cfg = json.load(fh)

    rows = load_manifest()
    seen = index_by_id(rows)
    added = 0

    for src in cfg["sources"]:
        if args.only and args.only.lower() not in src["name"].lower():
            continue
        if src.get("disabled"):
            continue
        log(f"  discover: {src['name']} (tier {src.get('tier')}, track {src.get('track')})")
        vids = discover_source(src, src.get("max_results"))
        kept = 0
        for v in vids:
            if v["id"] in seen:
                continue
            ok, reason = keep_video(v, src)
            if not ok:
                continue
            row = {
                "video_id": v["id"],
                "channel": src["name"],
                "title": html.unescape(v["title"] or ""),
                "duration": v["duration"] or "",
                "url": v["url"],
                "tier": src.get("tier", ""),
                "track": src.get("track", ""),
                "status": PENDING,
                "downloaded_at": "", "transcript": "", "extract": "", "notes": "",
            }
            rows.append(row)
            seen[v["id"]] = row
            kept += 1
            added += 1
        log(f"    found {len(vids)}, kept {kept}")
        if args.cap and added >= args.cap:
            log(f"    reached cap {args.cap}")
            break

    save_manifest(rows)
    log(f"discover: +{added} new pending rows ({len(rows)} total)")
    return 0


# ---------------------------------------------------------------- fetch subs

def cmd_fetch(args):
    if not ytdlp_available():
        log("yt-dlp not found. Install with: pip install -U yt-dlp")
        return 1
    rows = load_manifest()
    pending = [r for r in rows if r["status"] == PENDING]
    if args.limit:
        pending = pending[: args.limit]
    log(f"fetch: {len(pending)} pending")

    for i, r in enumerate(pending, 1):
        chan = safe_channel(r["channel"])
        outdir = os.path.join(RAW, chan)
        os.makedirs(outdir, exist_ok=True)
        tmpl = os.path.join(outdir, f"{r['video_id']}.%(ext)s")

        code, out, err = run_ytdlp([
            "--skip-download",
            "--write-subs", "--write-auto-subs",
            "--sub-langs", "en.*", "--sub-format", "vtt/srt/best",
            "--sleep-requests", str(args.sleep), "--sleep-subtitles", str(args.sleep),
            "--no-warnings", "--ignore-errors",
            "-o", tmpl, r["url"],
        ], timeout=240)

        got = [f for f in os.listdir(outdir)
               if f.startswith(r["video_id"] + ".") and f.endswith((".vtt", ".srt"))]
        if got:
            r["status"] = PENDING  # still needs cleaning; clean() promotes to done
            r["downloaded_at"] = now()
            r["notes"] = "subs:" + got[0].split(".", 1)[1]
            log(f"  [{i}/{len(pending)}] ok   {r['title'][:60]}")
        else:
            r["status"] = NO_SUBS
            r["notes"] = "no subtitles available"
            log(f"  [{i}/{len(pending)}] none {r['title'][:60]}")

        if i % 10 == 0:
            save_manifest(rows)

    save_manifest(rows)
    return 0


# ---------------------------------------------------------------- cleaning

TAG_RE = re.compile(r"<[^>]+>")
TS_RE = re.compile(r"^\d{1,2}:\d{2}:\d{2}[.,]\d{3}\s*-->")
SRT_IDX_RE = re.compile(r"^\d+$")
BRACKET_TS_RE = re.compile(r"^\[\d{1,2}:\d{2}(?::\d{2})?\]\s*")
NOISE_RE = re.compile(r"^\[(music|applause|laughter|inaudible|silence)\]$", re.I)


def _strip_cue_text(line):
    line = TAG_RE.sub("", line)
    line = html.unescape(line)
    line = re.sub(r"\s+", " ", line).strip()
    return line


def parse_subtitle_lines(text):
    """VTT/SRT -> ordered list of caption text lines (tags and timing removed)."""
    lines = []
    for raw_line in text.splitlines():
        s = raw_line.strip()
        if not s:
            continue
        if s.startswith("WEBVTT") or s.startswith("NOTE"):
            continue
        if s.startswith(("Kind:", "Language:", "STYLE", "REGION")):
            continue
        if TS_RE.match(s) or "-->" in s:
            continue
        if SRT_IDX_RE.match(s):
            continue
        s = _strip_cue_text(s)
        if not s or NOISE_RE.match(s):
            continue
        lines.append(s)
    return lines


def dedupe_rolling(lines, lookback=40):
    """
    Collapse the rolling-window artifact of YouTube auto-captions, where each cue
    repeats the tail of the previous cue before adding new words.

    Works at word level: for each incoming line, find the longest k such that the
    last k words already emitted equal the first k words of the line, then append
    only the remainder.
    """
    out = []
    for line in lines:
        words = line.split()
        if not words:
            continue
        if not out:
            out.extend(words)
            continue

        tail = out[-lookback:]
        max_k = min(len(tail), len(words))
        overlap = 0
        for k in range(max_k, 0, -1):
            if tail[-k:] == words[:k]:
                overlap = k
                break

        remainder = words[overlap:]
        if not remainder:
            continue  # fully contained repeat
        out.extend(remainder)
    return out


def collapse_repeats(words, max_k=16, min_k=2):
    """
    Collapse consecutive repeated word-groups.

    YouTube's rolling caption window shows ~2-3 lines at a time and re-sends the
    still-visible lines with each new cue. When a service flattens those cues into
    running text, every caption line appears 2-3 times back to back:

        "and welcome back to" x3 "another episode of" x3 ...

    Cross-line dedupe cannot see this because it is all one line, so collapse any
    k-gram that immediately repeats, preferring the longest match.
    """
    out = []
    i, n = 0, len(words)
    while i < n:
        collapsed = False
        upper = min(max_k, (n - i) // 2)
        for k in range(upper, min_k - 1, -1):
            gram = words[i:i + k]
            if gram == words[i + k:i + 2 * k]:
                out.extend(gram)
                j = i + k
                while words[j:j + k] == gram:
                    j += k
                i = j
                collapsed = True
                break
        if not collapsed:
            out.append(words[i])
            i += 1

    # caption stutter: 3+ identical consecutive words ("industry industry industry").
    # Doubles are left alone -- "no no" and "very very" are real speech.
    squashed, run = [], 0
    for w in out:
        run = run + 1 if squashed and w.lower() == squashed[-1].lower() else 0
        if run >= 2:
            continue
        squashed.append(w)
    return squashed


TRUNC_RE = re.compile(r"\[\s*\u2026?\.{0,3}\s*truncated at [\d,]+ characters\s*\]", re.I)


def strip_truncation_marker(text):
    """Returns (text, was_truncated). The upstream service caps very long transcripts."""
    if TRUNC_RE.search(text):
        return TRUNC_RE.sub("", text), True
    return text, False


def to_paragraphs(words, sentences_per_para=5, fallback_words=95):
    """Group a flat word list into readable paragraphs."""
    text = " ".join(words)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)

    # auto-captions often carry no punctuation at all -> chunk by length instead
    terminators = len(re.findall(r"[.!?]", text))
    if terminators < max(3, len(words) // 400):
        chunks, cur = [], []
        for w in words:
            cur.append(w)
            if len(cur) >= fallback_words:
                chunks.append(" ".join(cur))
                cur = []
        if cur:
            chunks.append(" ".join(cur))
        return chunks

    sentences = re.split(r"(?<=[.!?])\s+", text)
    paras, cur = [], []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        cur.append(s)
        if len(cur) >= sentences_per_para:
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    return paras


def clean_subtitle_text(text):
    words = dedupe_rolling(parse_subtitle_lines(text))
    return to_paragraphs(collapse_repeats(words))


def parse_inbox_text(text):
    """
    Clean a plain-text transcript fetched out-of-band (MCP transcript service).
    Strips its provenance header/footer and [m:ss] timestamps, then reflows.
    """
    body, _truncated = strip_truncation_marker(text)
    m = re.search(r"^##\s+Transcript\s*$", body, flags=re.M)
    if m:
        body = body[m.end():]
    body = re.split(r"^---\s*$\s*Generated by", body, flags=re.M)[0]

    lines = []
    for raw_line in body.splitlines():
        s = raw_line.strip()
        if not s:
            continue
        s = BRACKET_TS_RE.sub("", s)
        s = re.sub(r"\[\d{1,2}:\d{2}(?::\d{2})?\]", " ", s)
        s = _strip_cue_text(s)
        if not s or NOISE_RE.match(s):
            continue
        lines.append(s)
    return to_paragraphs(collapse_repeats(dedupe_rolling(lines)))


def write_transcript(row, paragraphs):
    chan = safe_channel(row["channel"])
    outdir = os.path.join(TRANSCRIPTS, chan)
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, safe_title(row["title"]) + ".md")

    words = sum(len(p.split()) for p in paragraphs)
    header = [
        f"# {row['title']}",
        "",
        f"- **Channel:** {row['channel']}",
        f"- **Duration:** {hms(row['duration']) or 'unknown'}",
        f"- **URL:** {row['url']}",
        f"- **Track:** {row.get('track','')} · **Tier:** {row.get('tier','')}",
        f"- **Words:** {words}",
        "",
        "---",
        "",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(header))
        fh.write("\n\n".join(paragraphs))
        fh.write("\n")
    return os.path.relpath(path, ROOT), words


def find_raw_sub(video_id, channel):
    outdir = os.path.join(RAW, safe_channel(channel))
    if not os.path.isdir(outdir):
        return None
    cands = sorted(f for f in os.listdir(outdir)
                   if f.startswith(video_id + ".") and f.endswith((".vtt", ".srt")))
    if not cands:
        return None
    # prefer manual subs (no "auto" marker) when both exist
    manual = [c for c in cands if "auto" not in c.lower()]
    return os.path.join(outdir, (manual or cands)[0])


def cmd_clean(args):
    rows = load_manifest()
    cleaned = 0
    for r in rows:
        if r["status"] == DONE and not args.force:
            continue
        if r["status"] in (NO_SUBS, SKIPPED):
            continue
        sub = find_raw_sub(r["video_id"], r["channel"])
        if not sub:
            continue
        with open(sub, encoding="utf-8", errors="replace") as fh:
            paras = clean_subtitle_text(fh.read())
        if not paras:
            r["status"] = NO_SUBS
            r["notes"] = "empty after cleaning"
            continue
        rel, words = write_transcript(r, paras)
        r["transcript"] = rel
        r["status"] = DONE
        r["downloaded_at"] = r["downloaded_at"] or now()
        r["notes"] = f"{words} words"
        cleaned += 1
    save_manifest(rows)
    log(f"clean: wrote {cleaned} transcripts")
    return 0


def cmd_ingest(args):
    """
    Import transcripts fetched out-of-band into the same shape as the yt-dlp path.

    Drop files at raw/_inbox/{video_id}.txt. Metadata comes from manifest.csv if the
    id is already there, otherwise from a sidecar raw/_inbox/{video_id}.json.
    """
    os.makedirs(INBOX, exist_ok=True)
    rows = load_manifest()
    by_id = index_by_id(rows)
    queue = load_queue()
    ingested = 0

    for fname in sorted(os.listdir(INBOX)):
        if not fname.endswith(".txt"):
            continue
        vid = fname[:-4]
        path = os.path.join(INBOX, fname)
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()

        row = by_id.get(vid)
        if row is None:
            side = os.path.join(INBOX, vid + ".json")
            meta = None
            if os.path.exists(side):
                with open(side, encoding="utf-8") as fh:
                    meta = json.load(fh)
            else:
                # fall back to the discovery queue, then to the file's own header
                meta = queue.get(vid)
                if meta is None:
                    _, htitle, hdur = parse_transcript_header(text)
                    if htitle:
                        meta = {"title": htitle, "duration": hdur}
            if meta is None:
                log(f"  ! {vid}: no manifest row, sidecar, or queue entry, skipped")
                continue
            row = {
                "video_id": vid,
                "channel": meta.get("channel", "unknown"),
                "title": meta.get("title", vid),
                "duration": meta.get("duration", ""),
                "url": meta.get("url", f"https://www.youtube.com/watch?v={vid}"),
                "tier": meta.get("tier", ""),
                "track": meta.get("track", ""),
                "status": PENDING,
                "downloaded_at": "", "transcript": "", "extract": "", "notes": "",
            }
            rows.append(row)
            by_id[vid] = row

        if row["status"] == DONE and not args.force:
            continue

        paras = parse_inbox_text(text)
        if not paras:
            row["status"] = NO_SUBS
            row["notes"] = "empty after cleaning"
            continue
        rel, words = write_transcript(row, paras)
        row["transcript"] = rel
        row["status"] = DONE
        row["downloaded_at"] = row["downloaded_at"] or now()
        side = os.path.join(INBOX, vid + ".json")
        trunc = False
        if os.path.exists(side):
            with open(side, encoding="utf-8") as fh:
                trunc = json.load(fh).get("truncated", False)
        row["notes"] = f"{words} words" + (" TRUNCATED-TAIL" if trunc else "")
        ingested += 1

    save_manifest(rows)
    log(f"ingest: wrote {ingested} transcripts")
    return 0


# ------------------------------------------------------- out-of-band adoption

HEADER_ID_RE = re.compile(r"Source video:\s*https?://\S*?[?&]v=([\w-]{11})")
HEADER_TITLE_RE = re.compile(r"^#\s*Transcript:\s*(.+?)\s*$", re.M)
HEADER_DUR_RE = re.compile(r"Duration:\s*(?:(\d+):)?(\d{1,2}):(\d{2})")


def parse_transcript_header(text):
    """Pull video_id / title / duration out of a fetched transcript's header block."""
    mid = HEADER_ID_RE.search(text)
    mt = HEADER_TITLE_RE.search(text)
    md = HEADER_DUR_RE.search(text)
    dur = ""
    if md:
        h, m, s = md.group(1), md.group(2), md.group(3)
        dur = str(int(h or 0) * 3600 + int(m) * 60 + int(s))
    return (mid.group(1) if mid else None,
            mt.group(1).strip() if mt else None,
            dur)


def extract_text_from_json(blob):
    """Some clients persist a tool result as JSON blocks: [{"type":"text","text":...}]."""
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return None
    parts = [b.get("text", "") for b in data if isinstance(b, dict) and b.get("type") == "text"]
    return "\n".join(parts) if parts else None


def load_queue():
    """seeds/queue.json maps video_id -> {channel, tier, track} discovered up front."""
    path = os.path.join(ROOT, "seeds", "queue.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {v["id"]: v for v in data.get("videos", []) if v.get("id")}


def cmd_adopt(args):
    """
    Import transcripts fetched by an out-of-band client (e.g. an MCP transcript tool
    whose large results are spilled to disk) into raw/_inbox, ready for `ingest`.
    """
    srcdir = args.results_dir
    if not os.path.isdir(srcdir):
        log(f"adopt: no such directory {srcdir}")
        return 1
    os.makedirs(INBOX, exist_ok=True)
    queue = load_queue()
    adopted, skipped = 0, 0

    for fname in sorted(os.listdir(srcdir)):
        if not fname.endswith((".txt", ".json")):
            continue
        path = os.path.join(srcdir, fname)
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        if fname.endswith(".json"):
            text = extract_text_from_json(text)
            if text is None:
                skipped += 1
                continue
        vid, title, dur = parse_transcript_header(text)
        if not vid:
            skipped += 1
            continue

        dest = os.path.join(INBOX, vid + ".txt")
        if os.path.exists(dest) and not args.force:
            skipped += 1
            continue

        _, truncated = strip_truncation_marker(text)
        meta = queue.get(vid, {})
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(text)
        with open(os.path.join(INBOX, vid + ".json"), "w", encoding="utf-8") as fh:
            json.dump({
                "title": meta.get("title") or title or vid,
                "channel": meta.get("channel", "unknown"),
                "duration": meta.get("duration") or dur,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "tier": meta.get("tier", ""),
                "track": meta.get("track", ""),
                "truncated": truncated,
            }, fh, indent=2)
        adopted += 1

    log(f"adopt: {adopted} adopted, {skipped} skipped")
    return 0


# ---------------------------------------------------------------- reporting

def link_extracts(rows):
    """Attach extract paths for rows whose extract file exists on disk."""
    for r in rows:
        p = os.path.join(EXTRACTS, safe_channel(r["channel"]), safe_title(r["title"]) + ".md")
        r["extract"] = os.path.relpath(p, ROOT) if os.path.exists(p) else ""
    return rows


def counts(rows):
    c = {}
    for r in rows:
        c[r["status"]] = c.get(r["status"], 0) + 1
    return c


def cmd_status(args):
    rows = link_extracts(load_manifest())
    c = counts(rows)
    done = [r for r in rows if r["status"] == DONE]
    log(f"rows={len(rows)} " + " ".join(f"{k}={v}" for k, v in sorted(c.items())))
    log(f"transcripts={sum(1 for r in done if r['transcript'])} extracts={sum(1 for r in done if r['extract'])}")
    log(f"track A={sum(1 for r in done if r['track']=='A')} track B={sum(1 for r in done if r['track']=='B')}")
    return 0


def word_count(relpath):
    p = os.path.join(ROOT, relpath)
    if not os.path.exists(p):
        return 0
    with open(p, encoding="utf-8", errors="replace") as fh:
        return len(fh.read().split())


def cmd_report(args):
    rows = link_extracts(load_manifest())
    save_manifest(rows)
    c = counts(rows)
    done = [r for r in rows if r["status"] == DONE]
    total_words = sum(word_count(r["transcript"]) for r in done if r["transcript"])

    log("=" * 62)
    log("  yt-kb — run report")
    log("=" * 62)
    log(f"  videos in manifest : {len(rows)}")
    log(f"  downloaded (done)  : {c.get(DONE,0)}")
    log(f"  no subtitles       : {c.get(NO_SUBS,0)}")
    log(f"  pending            : {c.get(PENDING,0)}")
    log(f"  skipped / error    : {c.get(SKIPPED,0)} / {c.get(ERROR,0)}")
    log(f"  transcripts on disk: {sum(1 for r in done if r['transcript'])}")
    log(f"  extracts on disk   : {sum(1 for r in done if r['extract'])}")
    log(f"  track A / track B  : {sum(1 for r in done if r['track']=='A')} / {sum(1 for r in done if r['track']=='B')}")
    log(f"  total transcript wc: {total_words:,}")
    log("-" * 62)
    log("  longest transcripts (proxy for depth):")
    ranked = sorted(((word_count(r["transcript"]), r) for r in done if r["transcript"]),
                    key=lambda x: -x[0])[:5]
    for w, r in ranked:
        log(f"    {w:>7,}  {r['channel'][:24]:<24} {r['title'][:44]}")
    log("=" * 62)
    return 0


# ---------------------------------------------------------------- entrypoint

def main():
    ap = argparse.ArgumentParser(description="yt-kb transcript pipeline (subtitles only)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover"); d.set_defaults(fn=cmd_discover)
    d.add_argument("--only", help="substring match on source name")
    d.add_argument("--cap", type=int, default=0, help="stop after N new rows")

    f = sub.add_parser("fetch"); f.set_defaults(fn=cmd_fetch)
    f.add_argument("--limit", type=int, default=150, help="max videos this run")
    f.add_argument("--sleep", type=int, default=2, help="politeness delay (seconds)")

    c = sub.add_parser("clean"); c.set_defaults(fn=cmd_clean)
    c.add_argument("--force", action="store_true")

    i = sub.add_parser("ingest"); i.set_defaults(fn=cmd_ingest)
    i.add_argument("--force", action="store_true")

    a = sub.add_parser("adopt"); a.set_defaults(fn=cmd_adopt)
    a.add_argument("--results-dir", required=True, help="directory of fetched transcript .txt files")
    a.add_argument("--force", action="store_true")

    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status)
    r = sub.add_parser("report"); r.set_defaults(fn=cmd_report)

    args = ap.parse_args()
    for p in (RAW, INBOX, TRANSCRIPTS, EXTRACTS):
        os.makedirs(p, exist_ok=True)
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
