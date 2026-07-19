# Media asset checklist — Seagrass for Manatees

Masters are committed under `media/assets/` (**under 2 MB each**).
Sync into Xibo Library folder `exhibits/seagrass-for-manatees`.

## Typography (CMS text widgets)

| Use | Font | Size / weight | Notes |
| --- | --- | --- | --- |
| Common name (Zone A) | Fraunces / sans fallback | ≥ 40 px, bold | Literal line breaks; no Markdown |
| Card title + bullets | Source Sans 3 / sans | ≥ 36 px, semi-bold | In `insights-copy` only |
| Ticker | Source Sans 3 / sans | ≥ 32 px | Single scrolling CTA line |

## Zone A — Hero ID

| Asset id | Filename | Status |
| --- | --- | --- |
| `graphic-manatee-id` | `graphic-manatee-id.png` | Present — transparent PNG in lower hero frame |
| `bg-hero-seagrass` | `bg-hero-seagrass.jpg` | Present — **800×1080** portrait wash (fills pane; no letterbox) |

## Zone B — Right pane + cards

| Asset id | Filename | Status |
| --- | --- | --- |
| `bg-insights-panel` | `bg-insights-panel.jpg` | Present — teal right-pane wash + soft divider |
| `bg-insights-copy-scrim` | `bg-insights-copy-scrim.png` | Present — opaque copy-band color sample (band color is painted in text widget) |
| `graphic-diet-seagrass` | `graphic-diet-seagrass.png` | Present — transparent card art |
| `graphic-threat-meadow` | `graphic-threat-meadow.png` | Present — transparent card art |
| `graphic-fact-nursery` | `graphic-fact-nursery.png` | Present — transparent card art |
| `graphic-help-protect` | `graphic-help-protect.png` | Present — transparent card art |

## Zone C — Ticker

| Asset id | Filename | Status |
| --- | --- | --- |
| `bg-ticker-scrim` | `bg-ticker-scrim.png` | Present — 1120×140 `#0B3D5C` sample (band color in text widget) |

## Preview thumbs

Tiny JPEGs under `media/previews/` referenced by `preview:` in `manifest.yaml`.

## Explicitly excluded

- Solid black mattes behind hero/card stills (use transparent PNGs)
- Markdown `**bold**` or emoji in CMS text widgets
- Text stacked over insight art (use `insights-art` + `insights-copy`)
