# Touch Hardware Demo

Ops exhibit: a **text-only** Glance & Match shell plus a native Xibo
**Interactive Button** (`Toggle info`) on the left pane. No HTML package and no
PNG/JPEG assets. Each tap runs a **Next Widget** action on the info playlist.

Layout name after CMS sync: `mmek-touch-demo`.

## What to check on the Pi

1. Left and right panes show instructional text.
2. The left pane shows a native **Toggle info** button (not a blank HTZ box).
3. Tap the button — the info label advances (Waiting for tap ↔ Touch works).
4. Tap again — the label advances again.

### Blank button box (Git LFS / CMS library)

The touch-toggle package is `touch-toggle.zip` in git (uploaded as `.htz`). If CMS
sync ran while that file was still an **LFS pointer stub**, the library holds an
invalid HTZ and the player shows an empty region even though text widgets work.

On the machine that runs **CMS preview sync**:

```bash
git lfs pull --include="exhibits/touch-demo/media/assets/touch-toggle.zip"
python3 tools/validate_exhibits.py --exhibit touch-demo --skip-secrets
```

Re-run preview sync, then let the Pi collect (or restart the player):

```bash
python3 tools/sync_cms.py --preview --exhibit touch-demo
```

`sync_media` and `upload_media` refuse LFS pointer files so a bad upload cannot
repeat. Delete stale `preview-touch-demo-touch-toggle` library rows only if sync
reuses a broken file without re-uploading (rare once sha256 tags match).

## Before scheduling

Confirm the panel USB touch cable is connected and HID is visible
([`ops/players/README.md`](../../ops/players/README.md)).

## Run on a lab Pi (`mmek-preview`)

1. **CMS preview sync** — Actions → **CMS preview sync** → your PR branch →
   **`exhibit`: `touch-demo`** → Run. This replaces layout **`mmek-preview`**.
   See [`ops/runbooks/cms-content-sync.md`](../../ops/runbooks/cms-content-sync.md).
2. **Schedule** — Bind campaign **`mmek-preview`** to the **preview** display
   group only (not lobby).
3. **Collect** — Let the player XMDS-collect (or restart the player service).
4. **CMS spot-check** — Layout **mmek-preview** should show text regions, an
   Interactive Button in **touch-toggle**, and an Interactive Action targeting
   **touch-info**.
5. Exercise **Toggle info** on the panel; remove the preview schedule when done.

Production stable name after merge: `mmek-touch-demo` (not used for branch preview).

## Notes

Content sync creates the Interactive Button and its touch → Next Widget action.
Manual Interactive Mode edits on `mmek-preview` are replaced on the next preview
sync.
