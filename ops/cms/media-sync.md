# Media store → Xibo sync

## Goal

Keep large masters out of Git while ensuring Xibo Library content matches each exhibit’s `media/manifest.yaml`.

## Prerequisites

- Media store reachable (NAS mount or S3-compatible API).
- CMS credentials available via env (see `ops/cms/README.md`).
- Manifest assets have real `sha256` values (not the stub zeros).

## Procedure

1. **Validate** manifests: `python tools/validate_exhibits.py` (or future CLI entrypoint).
2. **Fetch** from store by `uri` into a temp dir (or stream upload).
3. **Verify** downloaded bytes match `sha256`.
4. **Upload** to Xibo Library folder `exhibits/<slug>` if that hash/filename is missing or outdated.
5. **Apply tags** from `xiboTags` (always include `exhibit:<slug>`).
6. **Record** sync result in ops logs (optional); do not commit binaries.

## Content-addressed keys

Preferred store path:

```text
sha256/<first-two-hex>/<full-sha256>
```

Replacing media means a **new hash** and an updated manifest entry — never overwrite an existing key in place.

## Manual fallback

Until automation is complete:

1. Download the object from the store.
2. In CMS → Library → Add Media → save to `exhibits/<slug>`.
3. Add tags matching the manifest.
4. Replace media in layouts if the CMS “update in all layouts” option is appropriate.
