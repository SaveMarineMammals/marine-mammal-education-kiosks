# Touch Hardware Demo

Ops exhibit based on the Asian Small-Clawed Otters Glance & Match panel, plus one
extra **Show info / Hide info** control on the lower hero.

Layout name after CMS sync: `mmek-touch-demo`.

## What to check on the Pi

1. The otter Glance & Match layout renders (hero, insight cards, ticker).
2. Tap **Show info** on the lower-left control — a green info label appears.
3. Tap **Hide info** — the label disappears.

If the otter layout appears but the lower-left strip is blank, Arexibo is not
playing the small HTML package (`.htz`). The rest of the layout is intentionally
native image/text so a failed HTZ cannot blank the whole screen.

If **images show broken icons** but text widgets look fine, the player or CMS
host likely has **unresolved Git LFS pointers** instead of real binaries (common
when a clone skipped `git lfs pull`). On the sync host:

```bash
git lfs pull
python tools/validate_exhibits.py --exhibit touch-demo --skip-secrets
python tools/sync_cms.py --preview --exhibit touch-demo
```

Then trigger a layout collect on the Pi (or wait for XMDS) before re-testing.

## Before scheduling

Confirm the panel USB touch cable is connected and HID is visible
([`ops/players/README.md`](../../ops/players/README.md)).

## Run on a lab Pi (`mmek-preview`)

1. **CMS preview sync** — Actions → **CMS preview sync** → branch
   `feature/touch-demo-exhibit` (or your PR branch) → **`exhibit`: `touch-demo`**
   → Run. This replaces layout **`mmek-preview`** and uploads Library media as
   `preview-touch-demo-*` (tag `mmek:preview`). See
   [`ops/runbooks/cms-content-sync.md`](../../ops/runbooks/cms-content-sync.md).
2. **Schedule** — In CMS, bind campaign **`mmek-preview`** to the **preview**
   display group only (not lobby). The Pi playing your panel must be in that group.
3. **Collect** — After sync, let the player XMDS-collect (or restart the player
   service) so Library files download.
4. **CMS spot-check** — Library → `exhibits-preview/touch-demo/`: hero JPEG should
   be ~100KB+, not ~130-byte LFS pointer text. Layout **mmek-preview** should show
   assigned images in each image region and the touch-toggle HTZ in **touch-toggle**.
5. Exercise **Show info** / **Hide info**; remove the preview schedule when done.

Production stable name after merge: `mmek-touch-demo` (not used for branch preview).

## Out of scope

Xibo Interactive Actions (Button/Zone navigate to widget/layout) are not wired
by content sync. This demo uses a small offline HTML package for the toggle only.
