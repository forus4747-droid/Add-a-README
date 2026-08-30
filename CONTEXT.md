# Workspace Context

## Purpose

`Add-a-README` is organized as an ICM (Interpretable Context Methodology)
workspace: a Knowledge Bundle of two stable, self-contained deliverables
rather than a multi-step pipeline. Origin: a request to "run" the ICM
architecture (created by Jake Van Clief and David McDermott) to organize
Claude Code usage for lower token spend.

## Scope and a hard limit

This session runs in an isolated, ephemeral cloud container — it is not
the user's personal computer. Nothing here can reach or modify a real
local machine directly. `01_Token-Efficiency/` therefore produces
**portable, copyable** artifacts: files the user takes from this repo and
places into their own local `~/.claude` or project `.claude/` folders
themselves.

## Status

| Stage | State | Output |
|---|---|---|
| 01_Token-Efficiency | done | `claude-md-template.md`, `settings.efficient.json`, `practices.md` |
| 02_ICM-Reference | done | `methodology.md` |

## Variables

- Methodology source repos: `txmyer-dev/icm`, `RinDig/Interpretable-Context-Methodology`,
  `RinDig/icm-architect`, `ktnCodes/icm-template`.
- Paper: arxiv.org/abs/2603.16021 — "Interpretable Context Methodology:
  Folder Structure as Agent Architecture" (Van Clief & McDermott).
