# Research toolchain

All repos below were verified by cloning them on 18 Aug 2026 — existence and last-commit
dates are real, not taken from search summaries. Star counts are **not** included because
they could not be verified from this environment.

## The honest finding first

**A deep research agent would not have prevented the failure that prompted this.**

The Review Rescue offer died because one question was never asked — *does software already
do this?* — not because the searching was too shallow once asked. Four searches killed it.
A better research engine answers the question it is given; it does not know which question
kills the idea.

So the ordering is: **[`opportunity-screen`](../.claude/skills/opportunity-screen/SKILL.md)
decides what to ask. The engines below go deep once the screen says the question matters.**
An engine without the screen produces longer, better-cited reports about dead ideas.

## Engines

| Repo | Last commit | What it is | Cost to run |
|---|---|---|---|
| [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) | 2026-07-14 | Planner-executor-publisher agent, parallelised, cited reports. Best documented of the group. | `OPENAI_API_KEY` + `TAVILY_API_KEY`. Tavily has a free tier. ~$0.40/report on small models per third-party testing (WEAK — unverified). |
| [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) | 2026-08-10 | Smaller, configurable, LangGraph-based, swappable model/search/MCP providers. #6 on Deep Research Bench (0.4344). | Any provider key + a search API. |
| [Ayanami0730/deep_research_bench](https://github.com/Ayanami0730/deep_research_bench) | 2026-05-11 | The benchmark itself — 100 expert-written tasks across 22 fields. Use to judge engines rather than trusting vendor claims. | Free to read. |
| [DavidZWZ/Awesome-Deep-Research](https://github.com/DavidZWZ/Awesome-Deep-Research) | 2026-07-22 | Curated index of the field (ACL 2026). Start here when the landscape shifts. | Free. |

⚠️ **The `gpt-researcher` Claude skill is not the research agent.** Installed at
`.claude/skills/gpt-researcher`, its own description is for *"developers who want to
understand, extend, debug or integrate with GPT Researcher"*. It is documentation for
building on the tool. To actually run research you need `pip install gpt-researcher`
plus the API keys above.

## Signal sources for finding gaps

| Repo | Last commit | What it does |
|---|---|---|
| [Houseofmvps/reddit-intel-agent-mcp](https://github.com/Houseofmvps/reddit-intel-agent-mcp) | 2026-04-15 | Scores ideas against Reddit evidence across 7 dimensions — pain frequency, severity, workaround prevalence, competition weakness, recency, subreddit quality, noise. Maps directly onto gate 7. **Unreviewed — read before running.** |
| [michaelrockson/Problem-Identification-Agent](https://github.com/michaelrockson/Problem-Identification-Agent) | 2026-08-11 | Monitors communities for recurring pain points. **Unreviewed.** |
| [younis-ali/market-research-agent](https://github.com/younis-ali/market-research-agent) | 2024-03-21 | Competitor/opposition research. **Stale — over two years without a commit.** |

Neither of the first two has been read. Both run with full agent permissions. Review
before use, the same as any skill from a social feed.

## On Y Combinator

**Useful:** the method.
- **Paul Graham, [*How to Get Startup Ideas*](http://paulgraham.com/startupideas.html)** — organic ideas over manufactured ones; "live in the future and build what's missing"; keep a problem journal.
- **Paul Graham, [*Schlep Blindness*](http://paulgraham.com/schlep.html)** — the source of gate 6, and the single most useful idea here for someone without capital or audience.
- **YC Startup School** — free, and the evaluation frameworks transfer.

**Not useful as an idea source:** [YC's Requests for Startups](https://www.ycombinator.com/rfs).
The recent lists run to defence interceptors, compute at sea, robotics, and enterprise AI
memory layers — every one needs millions in funding and a technical team. It is a map of
where venture capital is pointed, which is close to the *opposite* of where a bootstrapped
solo operator should aim: YC wants markets big enough to return a fund, and those markets
are contested by companies with sales teams.

Reading RFS is worthwhile for the why-now signal in gate 5. Picking an idea off it is a
category error.

## What "hedge fund analyst" actually means here

Not more data. Analysts are not distinguished by having a bigger pile — they are
distinguished by:

1. **Falsification discipline** — trying to kill the thesis, hardest first, before committing
2. **Fast kills** — most ideas die in minutes, and that is the process working
3. **Source hierarchy** — knowing which numbers are load-bearing and cross-checking only those
4. **Naming the weakest link** — the gate that barely passed is what actually fails later
5. **Survivorship awareness** — the failures are missing from every public dataset

All five are encoded in `opportunity-screen`. The engines above supply depth. The screen
supplies the questions. Neither works without the other.
