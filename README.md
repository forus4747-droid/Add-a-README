# Add-a-README

A small ICM (Interpretable Context Methodology) workspace: folder
structure as agent architecture, applied here to cut Claude Code token
spend.

ICM was created by **Jake Van Clief** and David McDermott (Eduba /
University of Edinburgh). Numbered folders carry sequence, hierarchy
carries context scope, and plain markdown files carry state — a single
agent orients by reading the right file at the right moment instead of a
framework orchestrating multiple agents.

## Layout

```
Add-a-README/
├─ CLAUDE.md              agent entry point (routes, ~60 lines)
├─ CONTEXT.md             shared state for this workspace
├─ README.md              this file
├─ 01_Token-Efficiency/   copyable config for lower token spend
├─ 02_ICM-Reference/      condensed ICM methodology reference
└─ _catalog/              index and file-role classification
```

## Start here

- Working in this repo with an agent? Read `CLAUDE.md` first.
- Want the token-saving config for your own machine? Go to
  `01_Token-Efficiency/STAGE.md`.
- Want to understand or reapply ICM elsewhere? Go to
  `02_ICM-Reference/STAGE.md`.

## Note on scope

This was built from a remote, ephemeral Claude Code session, which has no
access to any other machine. Everything under `01_Token-Efficiency/` is
meant to be copied out and applied by hand to a real `~/.claude` or
project `.claude/` setup — nothing here executes itself.
