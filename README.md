# Canadian Business Acquisition — YouTube Transcript Knowledge Base

A local, grep-able text knowledge base about **buying and running small businesses in Canada**,
built from YouTube transcripts. Built for reading, not watching. No video is ever downloaded and
no video needs to be watched — **the transcripts are the product.**

**61 long-form videos · ~39 hours of talk · 350,000 words of transcript · 61 one-page extracts ·
four synthesis documents.**

---

## Start here

| Document | What it is |
|----------|------------|
| **[KNOWLEDGE.md](KNOWLEDGE.md)** | **Deal craft.** Top 20 lessons, a valuation cheat-sheet with multiples by industry, a due-diligence checklist, a 🇨🇦 Canadian deal-structure guide (CSBFP, VTB, share vs asset), and a glossary. 40 videos cited. |
| **[OPERATORS.md](OPERATORS.md)** | **What it's actually like to run these businesses.** One chapter per industry — janitorial, landscaping & snow, pest control, home services — each with a unit-economics table cited line by line, a staffing playbook, how contracts are won and lost, the top ten pains in owners' own words, and a **Seller BS Detector**. |
| **[INDEX.md](INDEX.md)** | Every video: title, channel, track, length, a one-line takeaway, and links to its extract and transcript. |
| **[QUESTIONS.md](QUESTIONS.md)** | What this corpus **could not** answer — unverified claims, Canadian gaps, contradictions between sources, and an honest table of where this build fell short. |

If you read one thing: **[OPERATORS.md](OPERATORS.md) §1 and the Seller BS Detector in each chapter.**
That is the part a listing will never tell you.

---

## The two tracks

Every video is classified into one of two tracks, and both matter equally.

**Track A — deal craft (31 videos).** Valuation, deal structure, financing, Canadian rules: CSBFP,
vendor take-backs, taxes, brokers, diligence. What you need to *buy* a business.

**Track B — operator reality (30 videos).** Staffing crews at 4am, bidding contracts, client churn,
the cash-flow gap in February, why owners burn out and sell. What you need to know before you *own*
one. **Track B is half the product, not garnish** — most acquisition content skips it entirely, which
is exactly why buyers get surprised on day two.

---

## Searching

```bash
./search.sh "vendor take-back"       # transcripts + extracts, with context
./search.sh -e "production rate"     # extracts only
./search.sh -t "DSCR"                # transcripts only
./search.sh -l "successor rights"    # just list matching files
```

Every extract carries a `tags:` line in its header, so tag search works too:

```bash
grep -rl 'tags:.*cash-flow' extracts/
grep -rh '^- \*\*tags:\*\*' extracts/ | tr ',' '\n' | sed 's/.*tags:\*\* //' | sort | uniq -c | sort -rn
```

Plain grep works fine — everything is markdown:

```bash
grep -ri "CSBFP" . --include='*.md'
```

---

## Layout

```
KNOWLEDGE.md      deal craft synthesis
OPERATORS.md      per-industry operator synthesis
INDEX.md          table of every video
QUESTIONS.md      open questions and known gaps
manifest.csv      pipeline state — one row per discovered video
sources.json      channels, search queries and filters used for discovery
pipeline.py       the pipeline (stdlib only)
run.sh            run the whole pipeline end to end
search.sh         corpus search helper
transcripts/      cleaned, readable transcripts, one folder per source
extracts/         one page per video, mirroring the transcripts/ tree
raw/              fetched captions — gitignored, regenerate rather than commit
```

`extracts/` mirrors `transcripts/` exactly, so any transcript path becomes its extract path by
swapping the first directory. Every citation in the synthesis documents is a path under `extracts/`
and every one of them resolves.

---

## The extract format

Each extract is **at most one page** and follows one of two templates.

**Track A:** Key numbers · What to look for (red and green flags) · Canadian-specific (US content is
marked *"US — verify for Canada"*) · Quotable lines (max 3) · Verdict.

**Track B:** Unit economics from the owner's mouth · Staffing reality · Winning work · The grind ·
Cash flow traps · Why owners quit or sell · What sellers hide · Quotable lines (max 3) · Verdict.

Every number in a synthesis document is cited to the extract it came from, in backticks, e.g.
`` `David-C-Barnett/Seller-Financing-To-Buy-A-Business-Vendor-Notes-in-M-A-Explained.md` ``.
Where two sources disagree, both are given — the disagreement is usually the finding.

---

## Running the pipeline

Requires [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and Python 3 (standard library only).

```bash
./run.sh                      # discover → download → clean → extract → report
python3 pipeline.py report    # summary of current state
```

The pipeline is **resumable**: `manifest.csv` holds one row per discovered video with its status, so
a re-run picks up where the last one stopped instead of re-fetching. Statuses are `pending`, `done`,
`no_subs` and `skipped`.

**Rules the pipeline enforces:**

- **Subtitles only. Video and audio are never downloaded** — `--write-auto-sub --skip-download`.
- **Be polite.** `--sleep-requests 2 --sleep-subtitles 2` between requests.
- **Long-form only.** Anything under **10 minutes** is skipped. Short-form does not contain
  operating detail worth reading.
- **Cap of ~150 videos per run.**

**One caveat about this corpus specifically:** the transcripts shipped here were *not* produced by
that code path. YouTube was unreachable from the build environment, so they were fetched one at a
time through a different route. The rules above still held in outcome — the shortest video in the
corpus is 10:30, and no media file was ever written — but `pipeline.py` has not been exercised
end to end against a live YouTube. See [QUESTIONS.md §4](QUESTIONS.md).

---

## Provenance and use

Transcripts are captions retrieved from YouTube for **personal study only.** They stay on this
machine and are **not republished.** Attribution to channel and video URL is preserved on every
transcript and every extract, and every claim in the synthesis documents traces back to a named
source. If you want the original, the URL is in `INDEX.md` — go watch it.

---

## Honest limits

Read **[QUESTIONS.md](QUESTIONS.md) §4** before trusting anything here. In short:

- The corpus is **61 videos, not the 150 originally targeted** — YouTube was unreachable directly in
  the build environment, so transcripts were fetched one at a time.
- Roughly **80% of sources are American.** Every US number is marked as such, and every place where
  Canada is likely to differ is flagged — but flagged is not verified.
- **Pest control is thin** (5 cited sources against a target of 8). The chapter says so rather than
  padding.
- **Every tax figure should be assumed stale.** Confirm the inclusion rate, the LCGE limit and the
  CSBFP caps for the year you actually transact.

Nothing in this repository is legal, tax or financial advice. It is a reading pile with the
citations kept.
