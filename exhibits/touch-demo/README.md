# Touch Hardware Demo

Ops exhibit: a **text-only** Glance & Match shell plus one large
**Show info / Hide info** control on the left pane. No PNG/JPEG assets —
native text always paints even if the HTML package fails.

Layout name after CMS sync: `mmek-touch-demo`.

## What to check on the Pi

1. Left and right panes show instructional text (not images).
2. Tap **Show info** in the large left-pane button — a green info label appears.
3. Tap **Hide info** — the label disappears.

If the text layout appears but the large left-pane box is blank, Arexibo is not
playing the HTML package (`.htz`). The rest of the layout is intentionally
native text so a failed HTZ cannot blank the whole screen.

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
   **`exhibit`: `touch-demo`** → Run. This replaces layout **`mmek-preview`**
   and uploads Library media as `preview-touch-demo-*` (tag `mmek:preview`).
   See [`ops/runbooks/cms-content-sync.md`](../../ops/runbooks/cms-content-sync.md).
2. **Schedule** — In CMS, bind campaign **`mmek-preview`** to the **preview**
   display group only (not lobby). The Pi playing your panel must be in that group.
3. **Collect** — After sync, let the player XMDS-collect (or restart the player
   service) so the HTZ downloads.
4. **CMS spot-check** — Layout **mmek-preview** should show text in the Glance &
   Match regions and the touch-toggle HTZ in **touch-toggle** (large left pane).
5. Exercise **Show info** / **Hide info**; remove the preview schedule when done.

Production stable name after merge: `mmek-touch-demo` (not used for branch preview).

## Out of scope

Xibo Interactive Actions (Button/Zone navigate to widget/layout) are not wired
by content sync. This demo uses a small offline HTML package with a CSS text
button only.
