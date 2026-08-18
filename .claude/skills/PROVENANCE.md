# Third-party skill provenance

Installed 18 Aug 2026. Both reviewed before install: pure-markdown instruction
files, no fetch-and-execute, no credential or data exfiltration patterns.

| Skill | Upstream | License | Commit |
|---|---|---|---|
| `vibesec-skill` | https://github.com/BehiSecc/VibeSec-Skill | Apache-2.0 | see below |
| `find-skills` | https://github.com/vercel-labs/skills (`skills/find-skills`) | see upstream | see below |

Local modification: `vibesec-skill` frontmatter `name` normalised from
`VibeSec-Skill` to `vibesec-skill` so it matches its directory. No other changes.

**Not installed: `claude-mem`** (https://github.com/thedotmack/claude-mem).
It is an npm package that installs session lifecycle hooks and a local SQLite
database. Its entire purpose is persisting memory across sessions on a durable
machine — this remote container is wiped when the session ends, so installing it
here would do nothing. Install it locally instead: `npx claude-mem install`

## Reviewed commits
```
BehiSecc/VibeSec-Skill    0590993b35ad51961f65a4d01cf1196dfead05bb
vercel-labs/skills        c6f69c631292444cc541ac6d91e2226b0ff247da
```
