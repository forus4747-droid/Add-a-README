# Build Your Own Coursera

A running implementation of the ["Build Your Own Coursera" guide](https://res.cloudinary.com/dailcoaeb/image/upload/vault/lead-magnets/build-your-own-coursera.pdf) by [Angus Sewell](https://angussewell.com): everything you save — YouTube videos, articles, links you text yourself — becomes study guides, briefing docs and quizzes, sorted by subject, generated overnight while you sleep.

```
You save a link → it lands in one table → the pipeline reads it
→ course material appears in Gemini Notebook → Telegram tells you
```

The pipeline is seven steps. Each is a small Python script in `scripts/` plus a matching Claude skill in `.claude/skills/`, deliberately separate so one bad step can never take the rest down:

| # | Skill | Script | What it does |
|---|-------|--------|--------------|
| 1 | `learning-capture` | `scripts/capture.py` | Reads your **Learn** playlist feed, adds new videos to the table (`status=new`) |
| 2 | `learning-inbox` | `scripts/inbox.py` | Picks up links you sent your **Telegram bot**, adds them (`status=new`) |
| 3 | `learning-fetch` | `scripts/fetch.py` | Gets the actual text — YouTube transcripts + web pages via Jina Reader (`status=fetched`) |
| 4 | `learning-sort` | `scripts/sort.py` | Classifies each item into a subject via the Claude API (`status=sorted`) |
| 5 | `learning-build` | `scripts/build.py` | Drives Gemini Notebook via `notebooklm-py`: one notebook per subject, study guide + briefing doc + quiz (`status=done`) |
| 6 | `learning-digest` | `scripts/digest.py` | Telegram message: what got built, grouped by subject, with notebook links |
| 7 | `learning-run` | `scripts/run_all.py` | Runs 1–6 once, in order; wire it to a daily 6am schedule |

**The status ladder, in order:** `new → fetched → sorted → done`. Anything that breaks goes to `failed` with the reason in the `error` field, so it never silently blocks the queue.

---

## Setup 1 — the one table everything lands in

The only thing you make by hand. Create a table called **Library** in [Baserow](https://baserow.io) (free to 3,000 rows) with these 12 fields:

| Field | Type | Notes |
|-------|------|-------|
| `url` | URL | the link you saved |
| `source` | Single select | `youtube` / `browser` / `telegram` / `sms` |
| `title` | Text | filled in by step 3 |
| `author` | Text | channel name or byline |
| `transcript` | Long text | the full text, filled in by step 3 |
| `topic` | Text | the subject, filled in by step 4 |
| `status` | Single select | `new` / `fetched` / `sorted` / `done` / `failed` |
| `notebook_id` | Text | filled in by step 5 |
| `added` | Date | when you saved it |
| `built` | Date | when the material was made |
| `note` | Long text | anything you typed when you saved it |
| `error` | Long text | why something failed, written by the pipeline |

You never type in this table — the pipeline fills every field. Open it any time to see what's queued, what's done, and what broke.

Then create a database token: Baserow → **My Settings → Database tokens** (needs create/read/update on the table). Note the table's numeric ID from its URL.

## Setup 2 — install and configure

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill it in
```

`.env` needs: `BASEROW_API_TOKEN`, `BASEROW_TABLE_ID`, `YT_PLAYLIST_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ANTHROPIC_API_KEY`. Never commit `.env` (it's gitignored).

## Setup 3 — open your doors into the table

**Door 1 — the Learn playlist.** On any YouTube video: Save → New playlist → call it **Learn**. Both of these settings are load-bearing:
- Visibility **Unlisted** (Private is invisible to every free method; Unlisted just means the feed link works).
- Ordering **Date added (newest)** — the feed only returns the first 15 slots, so with the default ordering your newest saves fall off the end and the whole thing quietly stops working after two weeks.

Copy the playlist ID from the address bar (the part after `list=`, starts with `PL`) into `.env`.

**Door 2 — a Telegram bot**, so you can save from your phone:
1. Message [@BotFather](https://t.me/BotFather), send `/newbot`, give it a name and username. It hands you a token.
2. Send your new bot any message, so a conversation exists.
3. Open `https://api.telegram.org/bot<YOUR-TOKEN>/getUpdates` in a browser and copy the `"chat":{"id": ...}` number — that's your chat ID.
4. Put both in `.env`. **That token is a password** — if it leaks, send `/token` to BotFather to rotate it.

(Doors 3 and 4 in the guide — a browser extension via a Make.com webhook relay, and a real SMS number — are optional and write into the same table; the pipeline picks them up identically.)

## Setup 4 — the bridge to Gemini Notebook (step 5 only)

Google publishes no consumer API for Gemini Notebook, so step 5 drives it with the open-source `notebooklm-py` CLI, **on your own computer**:

```bash
pip install "notebooklm-py[browser]>=0.8.0"   # 0.8.0+ is not optional
notebooklm login                              # opens a browser, sign in to Google
notebooklm auth check --test --json           # verify
```

If Google changes something and it breaks, steps 1–4 keep working and you add sources by hand until it's patched.

---

## Running it

Whole pipeline, once:

```bash
python scripts/run_all.py
```

Individual steps (`python scripts/run_all.py capture inbox fetch` also works):

```bash
python scripts/capture.py   # 1 — playlist → table
python scripts/inbox.py     # 2 — telegram → table
python scripts/fetch.py     # 3 — links → full text
python scripts/sort.py      # 4 — text → subjects
python scripts/build.py     # 5 — subjects → notebooks + material
python scripts/digest.py    # 6 — telegram summary
```

In Claude Code, the same steps are available as skills: `/learning-capture`, `/learning-inbox`, `/learning-fetch`, `/learning-sort`, `/learning-build`, `/learning-digest`, or `/learning-run` for the lot.

**You'll know it worked** when rows climb the status ladder in Baserow, one notebook per subject appears in Gemini Notebook with a study guide, briefing doc and quiz inside, and Telegram messages you a summary you didn't ask for.

### Set it running (step 7)

Run daily at 6am on the machine where `notebooklm login` was done (step 5 needs it, and the machine must be awake):

```bash
crontab -e
# 0 6 * * *  cd /path/to/this/repo && /usr/bin/python3 scripts/run_all.py >> pipeline.log 2>&1
```

Before trusting the schedule, run everything once by hand end to end (`python scripts/run_all.py`) and read the output. Telegram throws updates away after 24 hours, so daily is the minimum cadence for step 2.

---

## Details worth knowing

- **15 is the hard ceiling** on what the playlist feed shows at once. Save more than 15 things in a day → run capture twice. Same for fetch (15/run), sort (25/run) and build (20/run) — leftovers queue for the next run.
- **De-duplication:** videos match on video ID only (never the feed's published date); other links are compared after stripping `utm_` params, `si=`, and trailing slashes.
- **The Telegram offset** (`scripts/learning-offset.txt`) is saved only after every row was written — a failed run repeats nothing and loses nothing.
- **Short results are failures:** anything under 500 characters from fetch is treated as an error page or paywall, not content. A row is never marked `fetched` with an empty transcript.
- **Sorting is worth checking by hand for the first week.** Subject names become notebook names, and renaming later is a chore. Thin content lands in `Unsorted` rather than being guessed.
- **Build never marks a row `done`** unless the notebook got all three pieces of material, and never adds the same URL to a notebook twice.
- **The digest sets no parse mode**, so titles with brackets and underscores can't break the send; messages over 3,500 characters are split.
- **Swapping tools:** every function here has free alternatives (the guide lists six each for tables, readers, relays and digests). The reading tools live in two small functions in `scripts/fetch.py`; the digest is one `send()` in `scripts/digest.py`.
