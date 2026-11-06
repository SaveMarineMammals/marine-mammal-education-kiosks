# Media store → Xibo sync

## Goal

Keep **large** masters (video, files ≥ 2 MB) out of Git while ensuring Xibo Library content matches each exhibit’s `media/manifest.yaml`. Images and sound under 2 MB may be committed under `exhibits/<slug>/media/` and synced from the repo.

Prefer the orchestrator on the CMS host:

```bash
python tools/sync_cms.py --all-published --dry-run
python tools/sync_cms.py --all-published
# or single slug (must be published unless --force):
python tools/sync_media.py --exhibit <slug> --dry-run
python tools/sync_media.py --exhibit <slug>
```

Host install and triggers: [cms-content-sync.md](../runbooks/cms-content-sync.md).

## Prerequisites

- Media store reachable (`MEDIA_STORE_URI` as `file://` NAS mount or `s3://`).
- CMS credentials via env (`XIBO_CMS_URL`, `XIBO_CLIENT_ID`, `XIBO_CLIENT_SECRET`) — see `cms-sync.env.example`.
- Manifest assets have real `sha256` values (not the stub zeros).

## Procedure

1. **Validate** manifests: `python tools/validate_exhibits.py` (also run by `sync_cms.py` per slug).
2. **Resolve** each asset: repo-relative `uri` → read from Git tree; store `uri` → fetch from media store.
3. **Verify** bytes match `sha256`.
4. **Upload** to Xibo Library folder `exhibits/<slug>` if that hash/name is missing or outdated (reuse when tag `sha256:<first 43 hex digits>` matches).
5. **Apply tags** from `xiboTags` plus `exhibit:<slug>`, `mmek:managed`, and `sha256:<first 43 hex digits>`. Xibo rejects any tag longer than 50 characters, so the library tag cannot hold the full digest. The manifest still stores the full sha256, and sync verifies file bytes against that digest before upload.
6. Layout upsert (`mmek-<slug>`) is handled by `tools/sync_cms.py` / `tools/xibo_layout.py` — not by media-only CLI.

## Content-addressed keys

Preferred store path:

```text
sha256/<first-two-hex>/<full-sha256>
```

Replacing media means a **new hash** and an updated manifest entry — never overwrite an existing key in place.

## Manual fallback

If automation is unavailable:

1. Download the object from the store.
2. In CMS → Library → Add Media → save to `exhibits/<slug>`.
3. Add tags matching the manifest.
4. Rebuild or edit layout `mmek-<slug>` so playlists reference the new media.
