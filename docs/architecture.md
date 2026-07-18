# Architecture

## Role of this repository

This monorepo holds **exhibit source** (copy, layout recipes, media manifests) and **operations** (CMS conventions, Pi bootstrap, sync tooling). It does **not** replace Xibo.

| System | Responsibility |
| --- | --- |
| This repo | Source of truth for design, metadata, ops docs/scripts |
| Media store (NAS / S3-compatible) | Large masters (video, high-res stills, audio) |
| Xibo CMS | Library, layouts, schedules, display management |
| Xibo Linux Player (Raspberry Pi) | Playback on kiosk TVs |

## Content flow

```text
Author edits exhibit in Git
        |
        v
Masters land in media store (sha256 keys)
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

- **In Git:** YAML, copy, layout recipes, branding under ~2 MB, optional tiny preview thumbs.
- **Optional Git LFS:** stills/clips under ~5 MB when convenient early on.
- **Media store:** long video, large stills, audio beds — referenced by `sha256` and store URI in each exhibit’s `media/manifest.yaml`.
- **Not in Git:** `media/` working copies, `dist/` layout export ZIPs that embed full library files, secrets/credentials.

Prefer **content-addressed keys** in the store (e.g. `sha256/<hex-prefix>/<hex>`) so replacements are explicit and players/CMS caches stay coherent.

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
