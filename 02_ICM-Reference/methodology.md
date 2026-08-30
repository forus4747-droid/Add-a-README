# ICM — Interpretable Context Methodology

Created by **Jake Van Clief** and David McDermott (Eduba / University of
Edinburgh). Core claim: folder structure can replace framework-level
agent orchestration for sequential, human-reviewed workflows. Numbered
folders carry sequence, hierarchy carries context scope, plain markdown
files carry state — one agent orients by reading files at each step
instead of a framework coordinating multiple agents.

## Ten invariants

1. Single purpose per folder — each folder states its job internally.
2. Small entry file — `CLAUDE.md`, ~60 lines max, routes without holding content.
3. Numbering encodes sequence — `01_`, `02_` order the pipeline.
4. Explicit folder contracts — a `CONTEXT.md`/`STAGE.md` per folder states inputs, process, outputs.
5. Factory vs. product separation — stable reference material apart from run-specific outputs.
6. Outputs stay human-readable and editable, not just machine state.
7. Load only what's needed — a healthy stage file is ~2k-8k tokens.
8. Plain text, linkable (Markdown + YAML/wikilinks) — one home per fact.
9. Filesystem as state machine — status read from what exists, not separate metadata.
10. Instantiate by copying a template folder, never from a blank page.

## Two modes

- **Build** — extract structure from a description of a repeating
  workflow: find the unit of work, stable vs. changing elements, stopping
  points, deliverables; pick a form; scaffold minimally; write contracts.
- **Restructure** — audit an existing folder, classify every file as
  Catalog / Contract / Factory / Product / Dead, verify references,
  propose a migration map, migrate copy-verify-remove, then validate.
  (This workspace was built with Restructure mode.)

## Six workspace forms

Pipeline, Umbrella, Record Library, Knowledge Bundle, Context Map, System
Map — composable and recursive. This workspace is a **Knowledge Bundle**:
stable, independent reference documents rather than a stepwise pipeline.

## The walk test

An agent with no memory of this conversation should, from the entry file
plus two more reads, be able to answer "where am I," find each stage's
exact inputs/outputs, read pipeline status from what exists on disk, and
find no routing file carrying real content or any fact duplicated in two
places.

## Sources

- github.com/txmyer-dev/icm — original repo
- github.com/RinDig/Interpretable-Context-Methodology
- github.com/RinDig/icm-architect — the Claude skill (Build + Restructure modes)
- github.com/ktnCodes/icm-template — model-agnostic template
- arxiv.org/abs/2603.16021 — "Interpretable Context Methodology: Folder
  Structure as Agent Architecture" (Van Clief & McDermott)
