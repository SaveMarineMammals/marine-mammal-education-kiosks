# AGENTS.md — guide for AI coding agents

This file orients automated agents (Cursor, Copilot, CI bots, etc.) working in the
**Marine Mammal Education Kiosks** repository. Follow it together with
[docs/media-policy.md](docs/media-policy.md) and [docs/local-testing.md](docs/local-testing.md).

Tool-specific adapters (Cursor rules/skills, Copilot, Claude Code, …) should point
here instead of duplicating policy.

## Project context

This monorepo holds **exhibit source** (copy, layout recipes, media manifests) and
**operations** (CMS conventions, Pi bootstrap, QA) for Xibo-powered education
kiosks. It is the source of truth for design and in-repo media — **not** a
replacement for Xibo CMS or players.

| Path | Role |
| --- | --- |
| `exhibits/<slug>/` | One kebab-case exhibit package (YAML, copy, timeline, media manifest) |
| `framework/` | Shared branding, Glance & Match and other layout templates |
| `tools/` | Python CLI: validate, catalog, sync (stub), package, preview server |
| `ops/qa/` | Ephemeral Docker Xibo player capture + Chromium timeline preview |
| `schemas/` | JSON Schema for exhibit, catalog, and media manifests |

**Content flow:** Author in Git → images/sound under 2 MB in-repo → large/video in
media store → `tools/sync-media` / CMS Library → layouts & schedules → players via XMDS.

**Default tank-side template:** Glance & Match (`framework/layout-templates/glance-and-match/`).

## Before you change code

1. Read [docs/media-policy.md](docs/media-policy.md) — **required** for any media work.
2. Read [docs/local-testing.md](docs/local-testing.md) for Tier 1–3 quality checks.
3. For new exhibits, follow [docs/exhibit-authoring.md](docs/exhibit-authoring.md) and
   the [`exhibit-generator`](.agents/skills/exhibit-generator/SKILL.md) skill.
4. Identify whether the change belongs in `exhibits/`, `framework/`, `tools/`, or
   `ops/`; keep diffs scoped.
5. Do not commit secrets, `dist/` export ZIPs with embedded library media, video, or
   files ≥ 2 MB.

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
Exhibit assets under `exhibits/*/media/assets/` use **Git LFS** — CI and local
validation need real binaries (`git lfs pull`; Actions `lfs: true`).

### Exhibits

- One kebab-case slug per `exhibits/<slug>/`; register in `exhibits/_catalog.yaml`.
- Glance & Match is the default tank-side template; region ids and CMS-safe copy
  rules are in the exhibit-generator skill — do not invent `background`/`midground`
  regions for that template.
- Timeline text: YAML `|` blocks, plain ASCII, no Markdown/emoji; band color inside
  the text widget; CTA ticker via native Xibo `marqueeLeft` (see skill).

### Quality checks

Before opening a PR, run Tier 1 locally:

```powershell
python -m pip install -r tools/requirements.txt
python tools/validate_exhibits.py
python tools/catalog.py --check
```

Required on `main`: **Exhibit contract** and **Timeline preview** (path-filtered).
Live player Docker (`qa-player` label / nightly) is optional for merge but expected
before `status: published` — see [`ops/runbooks/publish-exhibit.md`](ops/runbooks/publish-exhibit.md).

## Git and PR expectations

- Work on feature branches; merge to `main` via PR only.
- Do not create commits unless the user asks.
- Do not push unless the user asks.
- PRs need green required CI, one non-pusher approval, resolved threads, linear
  history (squash/rebase merge) — see [`.github/rulesets/README.md`](.github/rulesets/README.md).
- Update docs when setup or author-visible behavior changes.
- Prefer focused diffs; avoid rewriting unrelated docs.

## Do not

- Commit secrets, `.env`, CMS credentials, or media-heavy Xibo export ZIPs
- Commit video or files ≥ 2 MB (use the media store)
- Invent Glance & Match region names that `ops/qa/exhibit_layout.py` does not know
- Put Markdown or emoji in timeline `copy:` fields
- Bypass branch protection instructions for users (except documented bypass actors)
- Finish exhibit/layout work without running Tier 1 validation on touched packages
- Over-engineer abstractions for one-off exhibit copy
- Run long-lived background processes in agent terminals without explicit user request

## Common tasks

| Task | Location |
| --- | --- |
| New Glance & Match exhibit | `.agents/skills/exhibit-generator/SKILL.md`, `exhibits/<slug>/` |
| Media policy / hashes | `docs/media-policy.md`, `exhibits/<slug>/media/manifest.yaml` |
| Contract validation | `tools/validate_exhibits.py`, `schemas/` |
| Timeline Chromium still | `ops/qa/ci_timeline_preview.py` |
| Live player capture | `ops/qa/run_qa_pipeline.py` |
| CI workflows | `.github/workflows/` |
| Branch protection | `.github/rulesets/` |

## Key documentation

| Document | Purpose |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Content flow, naming, media strategy |
| [docs/media-policy.md](docs/media-policy.md) | In-repo vs media-store binaries |
| [docs/exhibit-authoring.md](docs/exhibit-authoring.md) | New exhibit checklist |
| [docs/local-testing.md](docs/local-testing.md) | Tier 1–3 quality checks |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Human contributor workflow |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community standards |
| [README.md](README.md) | Overview and docs index |

When instructions conflict, **user request** > **this file** > **media-policy / exhibit-authoring** >
general defaults — but never skip required contract checks for exhibit or media
changes unless the user explicitly accepts that tradeoff.

## Tool adapters

| Tool | Adapter |
| --- | --- |
| Any (primary) | This `AGENTS.md` |
| Cursor rules | `.cursor/rules/*.mdc` (thin; point at `docs/`) |
| Cursor skills | `.cursor/skills/*/SKILL.md` (stubs → `.agents/skills/`) |
| Claude Code | Optional `CLAUDE.md` with `@AGENTS.md` only |
| GitHub Copilot | [`.github/copilot-instructions.md`](.github/copilot-instructions.md) → `@AGENTS.md` |
