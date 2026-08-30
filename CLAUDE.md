# Agent Entry Point

This workspace is organized with the Interpretable Context Methodology
(ICM): numbered folders carry sequence, hierarchy carries context scope,
plain markdown carries state. Do not read everything — orient here, then
open only the folder your task needs.

## Orient

1. Read `CONTEXT.md` for what this workspace is and its current status.
2. Pick a stage folder below and read only its `STAGE.md`.
3. Do not duplicate content from stage files back into this file — this
   file routes, it does not hold content.

## Stages

- `01_Token-Efficiency/` — copyable Claude Code config for cutting token
  spend on a real machine (CLAUDE.md template, settings.json, practices).
- `02_ICM-Reference/` — condensed reference on the ICM methodology itself
  and its source repos.

## Existing capability (do not restructure)

- `.claude/skills/youtube-to-agent/` — a working project skill, unrelated
  to the ICM workspace above. Leave as-is.

## Invariants

- Keep this file at or under ~60 lines.
- New work in a stage copies that stage's template folder; it does not
  start from a blank file.
- Every fact lives in exactly one file; other files link to it.
