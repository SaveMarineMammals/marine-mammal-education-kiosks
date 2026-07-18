# Template: layered-stills-loop

## Intent

Multi-region stills layout that feels animated without video. Independent overlapping
regions carry background textures, mid-ground graphics, foreground text, and a small
looping accent overlay. Scene changes use region entry/exit transitions (Fade / Slide).

## Canvas

- 1920×1080 landscape
- Total loop duration is exhibit-defined (typical 60–90s)

## Regions

| Region | Size / position | z-order | Content |
| --- | --- | --- | --- |
| background | 1920×1080 @ 0,0 | 0 | Full-bleed stills (`role: scene-bg`) |
| midground | 1920×1080 @ 0,0 | 1 | Transparent PNG graphics (`role: scene-graphic`) |
| text | 1600×280 @ 160,720 | 2 | Text / ticker widgets from exhibit `copy/` |
| accent | 280×280 @ 1580,40 | 3 | Looping PNG sequence or HTML package (`role: accent-loop`) |

Text region sits in the lower safe margin with a semi-opaque scrim for contrast
(see `framework/standards/accessibility.md`). Accent is a corner overlay that loops
for the full layout duration.

## Motion (no video)

- Stagger midground entrances 1–2s after the matching background.
- Prefer Fade for backgrounds; Slide In (left/right) for swimming/travel graphics.
- Use Text Fade In or Ticker Scroll for captions; keep motion gentle (no flashes).
- Accent region loops independently (bubbles, spout, or similar).

## CMS notes

- Tag media with `exhibit:<slug>` plus role tags (`role:scene-bg`, `role:scene-graphic`, `role:accent-loop`).
- Set layout duration to the exhibit loop length; playlist/schedule should loop the layout.
- Do not place video modules on this template.
