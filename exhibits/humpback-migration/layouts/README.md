# Layout recipe: Humpback Migration

**Template:** `framework/layout-templates/layered-stills-loop`  
**Layout duration:** 90 seconds (loop continuously)  
**Resolution:** 1920×1080 landscape  
**Constraint:** No video modules — motion from stills, text effects, and transitions only.

## Regions

| Region id | Size / position | z-order | Purpose |
| --- | --- | --- | --- |
| `background` | 1920×1080 @ 0,0 | 0 | Scene backgrounds (`role: scene-bg`) |
| `midground` | 1920×1080 @ 0,0 | 1 | Transparent PNG graphics (`role: scene-graphic`) |
| `text` | 1600×280 @ 160,720 | 2 | Scene copy from `copy/en.md` (scrim + Source Sans 3) |
| `accent` | 280×280 @ 1580,40 | 3 | Looping bubbles/spout (`accent-bubbles-loop`) |

Build in Xibo CMS using Library media tagged `exhibit:humpback-migration`.
Do not commit export ZIPs that embed full library media; place those under `dist/` if needed.

## Scene overview

| Scene | Window | Title | Primary assets |
| --- | --- | --- | --- |
| 1 | 0–15s | The Epic Journey | `bg-migration-map`, `graphic-migration-route`, `graphic-whale-swim` |
| 2 | 15–30s | The Cold Buffet | `bg-polar-seas`, `graphic-krill-school` |
| 3 | 30–45s | The Warm Nursery | `bg-tropical-ocean`, `graphic-mother-calf` |
| 4 | 45–60s | The Ocean's Gardeners | `bg-nutrient-depths`, `graphic-food-web` |
| 5 | 60–75s | The Journey's Dangers | `bg-open-ocean-muted`, `graphic-ship-silhouette`, `graphic-net-warning` |
| 6 | 75–90s | Be a Whale Hero | `bg-hero-splash`, `graphic-whale-tail` |

## Motion guidelines

- Backgrounds: **Fade** in/out at scene boundaries.
- Midground: stagger **+2s** after background; prefer **Slide In** for whale/travel graphics, **Fade** for icons.
- Text: **Fade In** at scene start +1s (or Ticker Scroll if a single line feels static).
- Accent: independent continuous loop for the full 90s.
- Keep transitions gentle per `framework/standards/accessibility.md`.

## Deliverables

1. **Media asset checklist** — [`../media/ASSETS.md`](../media/ASSETS.md)
2. **Widget timeline script** — [`timeline.yaml`](timeline.yaml)
