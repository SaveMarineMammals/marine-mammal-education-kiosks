# Marine Mammal Education Kiosks

Monorepo for an educational kiosk ecosystem powered by **Xibo CMS** (central) and **Xibo Linux Player** on Raspberry Pi displays.

This repository is the **source of truth for exhibit design and operations**. Xibo remains the deployed media library and schedule.

## Layout

| Path | Purpose |
| --- | --- |
| [`framework/`](framework/) | Shared branding, layout templates, widgets, playlists, standards |
| [`exhibits/`](exhibits/) | One folder per exhibit (grows over time) |
| [`ops/`](ops/) | CMS, Pi provisioning, networking, runbooks |
| [`tools/`](tools/) | CLI helpers (validate, sync, package, catalog) |
| [`docs/`](docs/) | Architecture and authoring guides |
| `media/` | Local working copies of **large** masters (**gitignored**) |
| `dist/` | Build/export artifacts (**gitignored**) |

## Framework vs exhibit

- **Framework** — anything two or more exhibits reuse (branding, templates, shared playlists).
- **Exhibit** — species/topic-specific copy, media manifests, layout instances, and schedule intent.

## Media policy

Only **large** files (≥ 2 MB, or any video) live in an external **media store** (NAS or S3-compatible bucket). **Images and sound under 2 MB each** may be committed under `exhibits/<slug>/media/` (or `framework/` when shared). Each exhibit’s `media/manifest.yaml` records hashes and either a repo-relative path or a store key. See [docs/architecture.md](docs/architecture.md).

## Adding an exhibit

1. Copy `exhibits/humpback-migration/` as a starting point.
2. Use a stable **kebab-case** slug for the folder name (do not rename after publish).
3. Fill in `exhibit.yaml`, `copy/`, `layouts/`, `media/manifest.yaml`, and `schedule/`.
4. Register the exhibit in [`exhibits/_catalog.yaml`](exhibits/_catalog.yaml).
5. Commit images/sound under 2 MB into `exhibits/<slug>/media/assets/`; stage larger masters under `media/<slug>/masters/` for the media store, then sync into Xibo.

## Quality checks (CI)

Pull requests to `main` must pass required GitHub checks:

| Check | When | What it does |
| --- | --- | --- |
| **Exhibit contract** | Every PR | Schema, catalog, media policy, Glance & Match timeline lint |
| **Timeline preview** | Layout/media/template changes (else skipped-as-pass) | Chromium still; non-black frame |

Optional live Xibo player capture: label a PR `qa-player`, run **Actions → QA player capture**, or follow the [publish runbook](ops/runbooks/publish-exhibit.md).

Same commands locally: [docs/local-testing.md](docs/local-testing.md).

## Docs

| Document | Description |
| --- | --- |
| [Architecture](docs/architecture.md) | Xibo + media flow |
| [Exhibit authoring](docs/exhibit-authoring.md) | How to add content |
| [Local testing](docs/local-testing.md) | Tier 1–3 validation on your machine |
| [Layout preview](framework/preview/) | Branding + template mockups in the browser |
| [Ops](ops/) | CMS, players, runbooks |
| [Publish exhibit](ops/runbooks/publish-exhibit.md) | Pre-publish QA gates |
| [AGENTS.md](AGENTS.md) | Guide for AI coding agents |
| [Contributing](CONTRIBUTING.md) | How to contribute |
| [Code of Conduct](CODE_OF_CONDUCT.md) | Community standards |

## License

Code and documentation in this repository: [Apache 2.0](LICENSE)

Copyright 2026 Marine Mammal Education Kiosks Contributors.

Exhibit media may carry separate attribution; see each exhibit’s `media/ASSETS.md`
and [framework/branding/attribution.md](framework/branding/attribution.md).

## Community

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md). Questions about authoring,
ops, or contribution scope can be opened as GitHub Discussions or issues.
