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

## Before scheduling

Confirm the panel USB touch cable is connected and HID is visible
([`ops/players/README.md`](../../ops/players/README.md)).

## Run on a lab Pi

1. Preview-sync this slug (`touch-demo`) onto `mmek-preview`, or sync the
   stable layout `mmek-touch-demo` — see
   [`ops/runbooks/cms-content-sync.md`](../../ops/runbooks/cms-content-sync.md).
2. Schedule that layout on the preview/lab display only.
3. Exercise the toggle; remove the schedule when finished.

## Out of scope

Xibo Interactive Actions (Button/Zone navigate to widget/layout) are not wired
by content sync. This demo uses a small offline HTML package for the toggle only.
