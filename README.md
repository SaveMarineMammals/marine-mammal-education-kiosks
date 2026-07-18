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

## Docs

- [Architecture](docs/architecture.md) — Xibo + media flow
- [Exhibit authoring](docs/exhibit-authoring.md) — how to add content
- [Local testing](docs/local-testing.md) — validate the repo and tools on your machine
- [Layout preview](framework/preview/) — branding + template mockups in the browser
- [Ops](ops/) — CMS, players, runbooks
