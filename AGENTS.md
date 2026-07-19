# Agent guidance

Portable instructions for AI coding agents working in this repository.
Tool-specific adapters (Cursor, Copilot, Claude Code, …) should point here
instead of duplicating policy.

## What this repo is

Marine mammal education **kiosk** content for Xibo: exhibit packages under
`exhibits/`, shared layout templates under `framework/`, and ops/QA under `ops/`.
This Git repo is the source of truth for copy, layout recipes, and in-repo media —
not a replacement for Xibo CMS or players.

## Read first

| Doc | When |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | Content flow, naming, media strategy |
| [`docs/media-policy.md`](docs/media-policy.md) | In-repo vs media-store binaries (always) |
| [`docs/exhibit-authoring.md`](docs/exhibit-authoring.md) | New exhibit checklist |
| [`framework/layout-templates/glance-and-match/`](framework/layout-templates/glance-and-match/) | Tank-side Glance & Match regions |
| [`ops/qa/README.md`](ops/qa/README.md) | Ephemeral player capture pipeline |

## Skills (task workflows)

Canonical Agent Skills live under [`.agents/skills/`](.agents/skills/):

| Skill | Use when |
| --- | --- |
| [`exhibit-generator`](.agents/skills/exhibit-generator/SKILL.md) | Creating or scaffolding a new Glance & Match exhibit |

Cursor keeps thin stubs under `.cursor/skills/` that defer to these files.

## Standing rules

### Media

Follow [`docs/media-policy.md`](docs/media-policy.md): images/sound **under 2 MB**
may be committed under `exhibits/<slug>/media/`; video and files **≥ 2 MB** go to
the external media store. Never commit secrets or media-heavy Xibo export ZIPs.

### Exhibits

- One kebab-case slug per `exhibits/<slug>/`; register in `exhibits/_catalog.yaml`.
- Glance & Match is the default tank-side template; region ids and CMS-safe copy
  rules are in the exhibit-generator skill — do not invent `background`/`midground`
  regions for that template.
- Timeline text: YAML `|` blocks, plain ASCII, no Markdown/emoji; band color inside
  the text widget; CTA ticker via native Xibo `marqueeLeft` (see skill).

### Commits and PRs

- Only commit when asked; do not push unless asked.
- Prefer focused diffs; avoid rewriting unrelated docs.

## Tool adapters

| Tool | Adapter |
| --- | --- |
| Any (primary) | This `AGENTS.md` |
| Cursor rules | `.cursor/rules/*.mdc` (thin; point at `docs/`) |
| Cursor skills | `.cursor/skills/*/SKILL.md` (stubs → `.agents/skills/`) |
| Claude Code | Optional `CLAUDE.md` with `@AGENTS.md` only |
| GitHub Copilot | Optional `.github/copilot-instructions.md` → `@AGENTS.md` |
