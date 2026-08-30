# Stage 01 — Token Efficiency

## Contract

- **Input:** none (stable reference stage — copy from here, don't edit in place).
- **Process:** none, this is a Factory folder: finished, reusable artifacts.
- **Output:** `claude-md-template.md`, `settings.efficient.json`, `practices.md`.
- **Gate:** none. Take what applies to your setup; nothing here is wired
  to auto-apply anywhere.

## How to use this on your real machine

1. Open `practices.md` first — it explains *why* each change saves tokens,
   so you copy the parts that fit your setup instead of all of it.
2. Adapt `claude-md-template.md` into your project's `CLAUDE.md` (or your
   global `~/.claude/CLAUDE.md`). Don't paste it verbatim — a `CLAUDE.md`
   full of facts your agent doesn't need is itself a token cost.
3. Merge the relevant blocks of `settings.efficient.json` into your own
   `~/.claude/settings.json` or project `.claude/settings.json` — don't
   overwrite your existing settings wholesale.
