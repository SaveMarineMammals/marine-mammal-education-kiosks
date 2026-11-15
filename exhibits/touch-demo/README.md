# Touch Hardware Demo

Ops-only exhibit that confirms which touch behaviors reach the Arexibo WebEngine
on a Raspberry Pi driving a USB-HID touchscreen (e.g. NovoTouch LK7530i).

**Not visitor education content.** Layout name after CMS sync: `mmek-touch-demo`.

## What it tests

| On-screen panel | Pass means |
| --- | --- |
| Event source chips | `touch*`, `pointer*`, and/or `mouse*` events reach the HTML widget |
| Finger markers | Multi-touch / simultaneous contacts |
| Tap pad | Single taps register |
| Drag canvas | Drag / swipe trails |
| Long-press target | Hold ~700 ms |
| Pinch target | Two-finger scale (may fail on some HID paths) |
| Corner / edge boxes | Hit mapping near screen extremes |
| Event log | Raw type, pointer id, and coordinates |

## Before scheduling

1. Confirm the panel USB touch cable is connected to the Pi.
2. Confirm HID is visible to the OS (`libinput` / commissioning checklist in
   [`ops/players/README.md`](../../ops/players/README.md)).

## Run on a lab Pi

1. Publish/sync this package to CMS (stable layout `mmek-touch-demo`), or use
   branch preview (`mmek-preview`) per
   [`ops/runbooks/cms-content-sync.md`](../../ops/runbooks/cms-content-sync.md).
2. Schedule that layout on the display group for the connected Pi only.
3. Interact on-panel; use the chips and event log to see which classes fire.
4. Remove the schedule (or restore attract) when finished.

Headless Docker QA skips HTML packages by default. Treat a **physical Pi** as
the acceptance gate for this exhibit.

## Out of scope

Xibo Interactive Actions (Button/Zone navigate to widget/layout) are not covered
here; validate those separately if needed on Arexibo.
