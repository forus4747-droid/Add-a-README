# Token-Efficiency Practices for Claude Code

Ranked by typical impact. Each item names the mechanism, not just the tip.

## 1. Every enabled MCP server and skill costs tokens before you type anything
Tool schemas and skill descriptions are loaded into context up front on
every turn. Disconnect MCP servers you aren't actively using this project
(`/mcp` to check status) and disable skills you don't need enabled
globally. Ten idle integrations can outweigh the actual conversation.

## 2. Keep CLAUDE.md small and stable
It's read every turn. Put only what an agent can't discover itself:
non-obvious constraints, where things live, house conventions. Don't
restate what a `README.md` or the code already says — link to it instead.
Long, drifting CLAUDE.md files are the single most common self-inflicted
context cost.

## 3. Prefer targeted reads over whole-file dumps
Use `Grep`/search to find the relevant lines, then `Read` with a line
range, rather than reading entire large files. Don't re-read a file you
just edited — the harness already knows the edit applied.

## 4. Delegate broad exploration, don't do it inline
A "search the whole codebase" question run directly in the main
conversation pulls every intermediate file into your main context
permanently. Delegating it to a subagent returns only the conclusion —
the search noise stays in the subagent's disposable context.

## 5. One task per session
Unrelated tasks in one long-running session keep accumulating context
that's irrelevant to the current one. Start a fresh session (or `/clear`)
per unrelated task rather than one session that does everything.

## 6. Let hooks do deterministic work instead of asking the agent to check
A pre-commit lint/format hook enforced by settings.json is free — it runs
without spending a turn on "now let me check formatting." Anything you
find yourself asking the agent to verify every single time is a hook
candidate.

## 7. Pre-approve safe, repeated commands
Every permission prompt the agent has to reason about and retry costs a
round trip. An allowlist of your common safe read-only commands
(see `settings.efficient.json`) removes that back-and-forth. (There's also
a `fewer-permission-prompts` skill that scans your own transcripts and
generates this list for you.)

## 8. Order context so the stable part comes first
Prompt caching keys off a stable prefix. Put unchanging material (project
facts, house style) before anything that changes turn to turn (current
diff, latest error) so more of the request hits cache instead of being
billed fresh.

## 9. Prune skills, don't just add them
Every additional skill's one-line description is loaded into every turn's
context to decide whether it's relevant. A large personal skill library
you rarely touch is a standing tax — periodically remove ones you no
longer use rather than only ever adding.
