# Local testing

How to verify this monorepo on a developer machine **without** needing Raspberry Pis or a full production CMS. Full TV playback still requires Xibo CMS + Xibo Linux Player (see the end of this doc).

## Prerequisites

- **Python 3.10+** on your PATH (preview server and exhibit CLI tools)
- Git (optional Git LFS only if you add binary previews under LFS rules)

From the repo root:

```powershell
cd C:\Users\jeff\Projects\marine-mammal-education-kiosks
```

## 1. Install tool dependencies

```powershell
python -m pip install -r tools/requirements.txt
```

This installs PyYAML for the exhibit/catalog tools. The preview server uses only the Python standard library.

## 2. Preview branding and layout templates

Serve from the **repo root** (not from `framework/preview/`):

```powershell
python tools/serve_preview.py
```

Open [http://localhost:4173/framework/preview/](http://localhost:4173/framework/preview/)

You should see token swatches, a type specimen, and three 1920×1080 template stages (scaled). Status should report that tokens loaded. Details: [framework/preview/README.md](../framework/preview/README.md).

This is a design aid only — final playback validation still needs Xibo.

## 3. Run the tooling smoke tests

```powershell
python tools/validate_exhibits.py
python tools/catalog.py --check
python tools/sync_media.py --exhibit humpback-migration --dry-run
python tools/package_exhibit.py --exhibit humpback-migration
```

### Expected results

| Command | Success looks like |
| --- | --- |
| `validate_exhibits.py` | `OK: 1 exhibit(s) passed structural validation` |
| `catalog.py --check` | `OK: catalog matches 1 exhibit(s)` |
| `sync_media.py --dry-run` | Lists planned Library uploads; ends with `Dry run only; no uploads performed.` |
| `package_exhibit.py` | Writes `dist/humpback-migration-checklist.txt` (under gitignored `dist/`) |

Validate a single exhibit:

```powershell
python tools/validate_exhibits.py --exhibit humpback-migration
```

## 4. Structure / contract smoke test

Confirm the exhibit contract catches mistakes:

1. Copy `exhibits/humpback-migration` to `exhibits/sea-otter-kelp`.
2. Update `id`, `slug`, and `title` in `exhibit.yaml`.
3. Set `exhibit:` in `media/manifest.yaml` to `sea-otter-kelp`.
4. Register it in the catalog:

   ```powershell
   python tools/catalog.py --write
   ```

   Or edit `exhibits/_catalog.yaml` by hand.
5. Re-run:

   ```powershell
   python tools/validate_exhibits.py
   python tools/catalog.py --check
   ```

6. Intentionally break a slug (folder name ≠ `exhibit.yaml` `slug`) and confirm validation fails, then fix it.

When finished experimenting, either keep the new exhibit as a real draft or delete the folder and run `python tools/catalog.py --write` again.

## 5. Media workflow (local files only)

Masters stay out of Git. Local authoring path:

1. Place a test file under `media/humpback-migration/masters/` (gitignored).
2. Compute a SHA-256 and record it in `exhibits/humpback-migration/media/manifest.yaml` with a store `uri` (use a placeholder until a real media store exists).
3. Confirm `validate_exhibits.py` still passes (it checks structure/slug alignment, not that the store object exists yet).

Live upload to Xibo is **not** implemented in `sync_media.py` yet — without `--dry-run` it exits with a “not implemented” message. Manual CMS upload steps are in [ops/cms/media-sync.md](../ops/cms/media-sync.md).

## 6. What this does *not* test yet

| Piece | Needs |
| --- | --- |
| Live media sync to CMS | Media store + Xibo API credentials (see [`.env.example`](../.env.example)) and a completed `sync_media.py` |
| Actual kiosk playback | Xibo CMS + Xibo Linux Player on a Pi (or Linux VM) |
| Layout rendering | Layouts built in the CMS from recipes under `framework/layout-templates/` |

## 7. Next: CMS + player integration test

When you are ready to test real playback:

1. Stand up **Xibo CMS Open Source Edition** (Docker is typical; see [ops/cms/README.md](../ops/cms/README.md)).
2. Copy `.env.example` to `.env` and fill CMS URL / API credentials (never commit `.env`).
3. Upload a small test video to Library folder `exhibits/humpback-migration` with tag `exhibit:humpback-migration`.
4. Build a layout from [framework/layout-templates/full-bleed-video](../framework/layout-templates/full-bleed-video/).
5. Enroll a test display (Pi or supported Linux player) per [ops/players/README.md](../ops/players/README.md).
6. Schedule the layout to a **display group** (e.g. `lobby`) and confirm playback, then optionally follow [ops/runbooks/offline-cache.md](../ops/runbooks/offline-cache.md).

## Related docs

- [Architecture](architecture.md)
- [Exhibit authoring](exhibit-authoring.md)
- [Layout preview](../framework/preview/README.md)
- [Publish runbook](../ops/runbooks/publish-exhibit.md)
- [Content checklist](../framework/standards/content-checklist.md)
