# Media storage policy

Only **large** binaries belong in the external media store. Agents must not treat all
media as store-only.

## Keep in this repo (Git)

- **Images** and **sound** files are allowed under `exhibits/<slug>/media/` (or
  `framework/` when shared) when **each file is under 2 MB**.
- Prefer `exhibits/<slug>/media/assets/` for exhibit stills/audio and
  `exhibits/<slug>/media/previews/` for tiny thumbs.
- Record every committed asset in `media/manifest.yaml` with a real `sha256`,
  `mime`, `bytes`, and a **repo-relative** `uri` (e.g.
  `exhibits/humpback-migration/media/assets/graphic-whale-swim.png`).

## Use the external media store

- Files **≥ 2 MB**, **video**, layout export ZIPs with embedded library media, and
  other oversized masters.
- Stage large masters under root `media/<slug>/masters/` (gitignored), upload to
  the store, then set `uri` to a content-addressed store key
  (`sha256/<prefix>/<hash>`).

## Do not

- Commit anything ≥ 2 MB to Git.
- Commit secrets, CMS credentials, or media-heavy Xibo export ZIPs (those go under
  gitignored `dist/`).
- Put shared multi-exhibit assets only under one exhibit — promote them to
  `framework/`.

Canonical architecture detail: [`architecture.md`](architecture.md) (Media strategy).
