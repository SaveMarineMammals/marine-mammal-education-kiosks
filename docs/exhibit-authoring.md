# Exhibit authoring

## Checklist for a new exhibit

1. Choose a **kebab-case** slug that will not change after publish.
2. Create `exhibits/<slug>/` from the `humpback-migration` stub.
3. Fill `exhibit.yaml` (see [schemas/exhibit.schema.json](../schemas/exhibit.schema.json)).
4. Add curator notes and learning goals to `README.md`.
5. Write visitor-facing text under `copy/`.
6. Document layout intent under `layouts/` (recipe markdown; CMS export ZIPs go to `dist/`, not Git).
7. List media in `media/manifest.yaml` with store URIs and SHA-256 hashes.
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
    previews/          # optional tiny thumbs committed to Git
  schedule/
  checksums.sha256     # optional package integrity file
```

## Media workflow

1. Place masters in local `media/<slug>/masters/` (gitignored).
2. Compute SHA-256 and upload to the media store under a content-addressed key.
3. Update `media/manifest.yaml` with `id`, `role`, `filename`, `sha256`, `uri`, `mime`, and `xiboTags`.
4. Sync into Xibo Library (folder + `exhibit:<slug>` tag) via ops tooling or CMS UI.
5. Build/update layouts in CMS using Library search — do not commit full export ZIPs with embedded media.

## Resolution and duration

Follow [`framework/standards/`](../framework/standards/) for canvas size (default 1920×1080), safe margins, and recommended durations.
