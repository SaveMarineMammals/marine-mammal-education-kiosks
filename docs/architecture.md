# Architecture

## Role of this repository

This monorepo holds **exhibit source** (copy, layout recipes, media manifests) and **operations** (CMS conventions, Pi bootstrap, sync tooling). It does **not** replace Xibo.

| System | Responsibility |
| --- | --- |
| This repo | Source of truth for design, metadata, ops docs/scripts |
| Media store (NAS / S3-compatible) | Large masters only (video, files ≥ 2 MB) |
| Xibo CMS | Library, layouts, schedules, display management |
| Xibo Linux Player (Raspberry Pi) | Playback on kiosk TVs |

## Content flow

```text
Author edits exhibit in Git
        |
        +-- images/sound under 2 MB committed under exhibits/<slug>/media/
        |
        +-- large/video masters → media store (sha256 keys)
        |
        v
tools/sync-media uploads changed files into Xibo Library
        |
        v
Layouts / playlists in CMS reference Library media
        |
        v
Schedule binds campaigns to display groups
        |
        v
Players pull layouts + media via XMDS
```

## Media strategy

Only **large** files should be referenced from the external media store. Images and sound may live in this repo when each file is under **2 MB**.

- **In Git:** YAML, copy, layout recipes; **images and sound under 2 MB each** (typically under `exhibits/<slug>/media/assets/` or shared `framework/`); optional preview thumbs.
- **Media store:** video and any file **≥ 2 MB** — referenced by `sha256` and store URI in each exhibit’s `media/manifest.yaml`.
- **Not in Git:** root `media/` working copies of large masters, `dist/` layout export ZIPs that embed full library files, secrets/credentials.

Manifest `uri` values are either **repo-relative paths** (in-repo assets) or **content-addressed store keys** (e.g. `sha256/<hex-prefix>/<hex>`) so replacements stay explicit and players/CMS caches stay coherent.

## Naming conventions

| Concept | Convention | Example |
| --- | --- | --- |
| Exhibit slug | kebab-case; stable after publish | `humpback-migration` |
| Git folder | `exhibits/<slug>/` | `exhibits/humpback-migration/` |
| Xibo Library folder | mirrors slug | `exhibits/humpback-migration` |
| Xibo tag | `exhibit:<slug>` | `exhibit:humpback-migration` |
| Display groups | location/role, not exhibit | `lobby`, `classroom-a` |
| Player hostname | `kiosk-<location>-<nn>` | `kiosk-lobby-01` |

## Framework vs exhibit

- Put shared branding, layout templates, custom widget XML, and idle/attract playlists in `framework/`.
- Put species facts, exhibit-specific media, learning goals, and schedule intent in `exhibits/<slug>/`.
- If two or more exhibits need an asset, promote it to `framework/`.

## Status lifecycle

Exhibits use `status` in `exhibit.yaml`: `draft` → `review` → `published` → `retired`. Prefer retiring over deleting so history and checksums remain auditable.
