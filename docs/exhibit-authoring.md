# Exhibit authoring

## Checklist for a new exhibit

1. Choose a **kebab-case** slug that will not change after publish.
2. Create `exhibits/<slug>/` from the `humpback-migration` stub.
3. Fill `exhibit.yaml` (see [schemas/exhibit.schema.json](../schemas/exhibit.schema.json)).
4. Add curator notes and learning goals to `README.md`.
5. Write visitor-facing text under `copy/`.
6. Document layout intent under `layouts/` (recipe markdown; CMS export ZIPs go to `dist/`, not Git).
7. List media in `media/manifest.yaml` (repo paths for ≤2 MB images/sound; store URIs for large/video files) with SHA-256 hashes.
8. Record intended display groups / dayparts under `schedule/`.
9. Add an entry to [`exhibits/_catalog.yaml`](../exhibits/_catalog.yaml).
10. Validate with `tools/validate-exhibits` (when implemented).

## Directory contract

```text
exhibits/<slug>/
  exhibit.yaml
  README.md
  copy/
  layouts/
  media/
    manifest.yaml
    assets/            # images & sound under 2 MB each (committed)
    previews/          # optional tiny thumbs committed to Git
  schedule/
  checksums.sha256     # optional package integrity file
```

## Media workflow

1. **Images and sound under 2 MB:** commit under `exhibits/<slug>/media/assets/` (or `framework/` if shared). Record `sha256`, `bytes`, `mime`, and a repo-relative `uri` in `media/manifest.yaml`.
2. **Video or any file ≥ 2 MB:** place masters in local `media/<slug>/masters/` (gitignored), upload to the media store under a content-addressed key, and set `uri` to that store key in the manifest.
3. Sync into Xibo Library (folder + `exhibit:<slug>` tag) via ops tooling or CMS UI — from the repo path or the store, as appropriate.
4. Build/update layouts in CMS using Library search — do not commit full export ZIPs with embedded media.

## Resolution and duration

Follow [`framework/standards/`](../framework/standards/) for canvas size (default 1920×1080), safe margins, and recommended durations.
