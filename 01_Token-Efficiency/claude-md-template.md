<!--
Template for a real project's CLAUDE.md. Delete every section that
doesn't apply — an unused section still costs tokens every turn.
Target: under ~100 lines for a typical project.
-->

# Project

One or two lines: what this project is, who it's for.

## Non-obvious constraints

- Only facts an agent cannot discover by reading the code itself.
- e.g. "migrations run only via `make migrate`, never `alembic` directly"

## Where things live

- Bullet list of directories/files an agent would otherwise have to
  search for repeatedly (config, entry point, test runner).

## Conventions

- House rules that aren't visible from the code alone (naming, commit
  format, branch strategy) — link to a longer doc instead of pasting it
  if it's more than a few lines.

## Commands

- `test:` ...
- `lint:` ...
- `build:` ...

<!-- Do not restate what package.json/Makefile/README already say. -->
