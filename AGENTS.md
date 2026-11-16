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
| `tools/` | Python CLI: validate, catalog, CMS sync, package, preview server |
| `ops/qa/` | Ephemeral Docker Xibo player capture + Chromium timeline preview |
| `schemas/` | JSON Schema for exhibit, catalog, and media manifests |

**Content flow:** Author in Git → images/sound under 2 MB in-repo → large/video in
media store → `tools/sync_cms.py` (Library + `mmek-<slug>` layouts) → operator
schedules in CMS → players via XMDS.

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

### Interactivity (no HTML widgets on facility players)

Facility Pis run **Arexibo**, which does **not** reliably play HTML packages
(`.htz` / `html-package`), embedded HTML, or full-canvas `html-interactive`
layouts — regions render blank. Do **not** author new touch or interactive demos
with HTML packages, offline HTML zips, or embedded HTML widgets.

Use **native Xibo widgets and Interactive Actions** instead:

- Interactive Button / Link / Zone (`type: interactive-button` in timeline YAML)
- Touch → Next/Previous Widget or Navigate to Widget/Layout actions (wired by
  `tools/xibo_layout.py` / content sync when declared on the timeline widget)
- Image and text widgets for everything else

Reference: [`exhibits/touch-demo/`](exhibits/touch-demo/) (ops touch validation).
Headless QA may still skip or stub HTML packages; that does not make them valid
for production layouts.

### Shell scripts (LF only)

Linux hosts (CMS, Pis, containers) fail shebangs with
`env: 'bash\r': No such file or directory` when a `.sh` file has Windows **CRLF**
endings. [`.gitattributes`](.gitattributes) sets `*.sh text eol=lf`, but editors and
agent file writers on Windows can still produce CRLF on disk.

- Always write and save `*.sh` with **LF** line endings (no `\r`).
- After creating or editing a shell script on Windows, verify before `scp`/commit:
  `python -c "from pathlib import Path; p=Path('path/to/script.sh'); d=p.read_bytes(); assert d.count(b'\r')==0, 'CRLF'; print('LF ok')"`
  If CRLF is present: rewrite with `d.replace(b'\r\n', b'\n').replace(b'\r', b'\n')`.
- Prefer `git add` (clean filter) over raw `scp` of a dirty working tree; if you must
  copy outside Git, confirm the remote `head -1 file | od -An -tx1` ends in `0a`
  only (not `0d 0a`).

### Runtime version pins (QA ↔ production)

Keep facility and ephemeral QA stacks on **compatible, pinned** Xibo versions.
Do not float “latest” channel tips in CI or golden images without a deliberate
upgrade + capture validation.

| Layer | Canonical pin | Notes |
| --- | --- | --- |
| Facility / QA CMS | `ghcr.io/xibosignage/xibo-cms:…` in [`ops/qa/docker-compose.test.yml`](ops/qa/docker-compose.test.yml) | QA compose tag should match (or be explicitly compatible with) the facility CMS Docker bundle. Bump both together when upgrading CMS. |
| Pi kiosk player | [`ops/players/image/stage-kiosk/01-arexibo/AREXIBO_VERSION`](ops/players/image/stage-kiosk/01-arexibo/AREXIBO_VERSION) + [`ops/players/image/vendor/arexibo.manifest.yaml`](ops/players/image/vendor/arexibo.manifest.yaml) | Production uses **Arexibo** (arm64 `.deb`), not the Snap Store player. Keep `AREXIBO_VERSION`, manifest `version`/`sha256`/`release_tag`, and `player-image.yml` in sync. |
| QA headless player | `XIBO_PLAYER_SNAP_REVISION` in [`ops/qa/Dockerfile.player`](ops/qa/Dockerfile.player) / [`ops/qa/config.env.example`](ops/qa/config.env.example) | Ephemeral Docker QA extracts the **xibo-player** snap (no snapd). Pin revision **108 (1.8-R6)** today — `latest/stable` is Chromium 4.x and breaks `bin/player` + the Boost QA shim. |

Rules for agents:

- When changing any pin above, update the table’s files in the **same PR** and note
  upgrade debt (Qt ABI, snap layout, CMS API) in the PR body.
- Do not set QA to an unpinned Snap `stable` tip, and do not bump Arexibo past the
  mirrored manifest without a Pi image rebuild + soak.
- After player or CMS pin changes, run **QA player capture**
  (`ops/qa/run_qa_pipeline.py` or the `QA player capture` workflow) before treating
  the change as done.
- Pi Arexibo and the QA snap are different binaries; “consistent” means **compatible
  CMS protocol / layout behavior**, not identical package names. Prefer upgrading the
  QA image toward production’s player generation when facility moves off 1.8-era
  assumptions — do not silently diverge.

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
- Author new `html-package` / `.htz` / embedded-HTML interactivity for facility
  layouts — use native Interactive Button + Actions (see Interactivity above)
- Bypass branch protection instructions for users (except documented bypass actors)
- Finish exhibit/layout work without running Tier 1 validation on touched packages
- Over-engineer abstractions for one-off exhibit copy
- Run long-lived background processes in agent terminals without explicit user request
- Write or ship `*.sh` with CRLF line endings (breaks Linux shebangs; see Shell scripts above)

## Common tasks

| Task | Location |
| --- | --- |
| New Glance & Match exhibit | `.agents/skills/exhibit-generator/SKILL.md`, `exhibits/<slug>/` |
| Touch / interactive (native only) | `exhibits/touch-demo/`, Interactive Button + Actions in `tools/xibo_layout.py` |
| Media policy / hashes | `docs/media-policy.md`, `exhibits/<slug>/media/manifest.yaml` |
| Contract validation | `tools/validate_exhibits.py`, `schemas/` |
| CMS content sync (media + layouts) | `tools/sync_cms.py`, `ops/cms/scripts/deploy-cms-sync.sh`, `ops/runbooks/cms-content-sync.md` |
| CMS branch preview (manual) | `.github/workflows/cms-preview.yml`, `tools/sync_cms.py --preview`, `ops/runbooks/cms-content-sync.md` |
| Facility DNS / ACME IAM (Terraform) | `infra/`, `docs/infra-pipelines.md`, `ops/cms/caddy/` |
| Security patching + admin alerts | `ops/runbooks/security-patching.md`, `ops/runbooks/sent-dm-alerts.md`, `infra/terraform/modules/admin-alert/` |
| Facility Tailscale (CMS + players) | `ops/runbooks/facility-tailscale.md`, `ops/cms/scripts/install-tailscale.sh` |
| Timeline Chromium still | `ops/qa/ci_timeline_preview.py` |
| Live player capture | `ops/qa/run_qa_pipeline.py` |
| Golden Pi image / kiosk config | `ops/players/image/`, `.github/workflows/player-image.yml` |
| CI workflows | `.github/workflows/` |
| Branch protection | `.github/rulesets/` |

## Key documentation

| Document | Purpose |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Content flow, naming, media strategy |
| [docs/facility-physical-setup.md](docs/facility-physical-setup.md) | NovoTouch LK7530i + Pi VESA physical install |
| [ops/players/image/](ops/players/image/) | Reproducible Pi image + per-kiosk config generator |
| [docs/media-policy.md](docs/media-policy.md) | In-repo vs media-store binaries |
| [docs/exhibit-authoring.md](docs/exhibit-authoring.md) | New exhibit checklist |
| [docs/local-testing.md](docs/local-testing.md) | Tier 1–3 quality checks |
| [ops/runbooks/cms-content-sync.md](ops/runbooks/cms-content-sync.md) | Git main → Xibo media/layouts; optional branch preview (`mmek-preview`) |
| [ops/runbooks/security-patching.md](ops/runbooks/security-patching.md) | Off-hours OS/stack updates + Lambda alerts |
| [ops/runbooks/sent-dm-alerts.md](ops/runbooks/sent-dm-alerts.md) | Sent.dm SMS template + API key for alerts |
| [docs/infra-pipelines.md](docs/infra-pipelines.md) | AWS Terraform CI + Route 53 / LE DNS-01 / admin-alert |
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
