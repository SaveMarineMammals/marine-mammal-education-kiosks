# Layout recipe: Seagrass for Manatees

**Template:** `framework/layout-templates/glance-and-match`  
**Layout duration:** 24 seconds (4 × 6s insight cards; loop continuously)  
**Resolution:** 1920×1080 landscape  
**Constraint:** Zone A is permanently static. No video modules required.

## Regions

| Region id | Zone | Size / position | z-order | Purpose |
| --- | --- | --- | --- | --- |
| `insights-bg` | B/C | 1120×1080 @ 800,0 | 0 | Right-pane teal wash |
| `hero-bg` | A | 800×1080 @ 0,0 | 1 | Portrait seagrass wash (fills pane — no letterbox) |
| `hero-still` | A | 720×740 @ 40,300 | 2 | Transparent manatee ID in lower frame |
| `hero-labels` | A | 752×260 @ 24,24 | 3 | Name + metrics |
| `insights-art` | B | 1040×440 @ 840,32 | 2 | Paging card graphics only |
| `insights-copy` | B | 1040×280 @ 840,500 | 3 | Card bullets; band color inside text widget |
| `ticker` | C | 1120×140 @ 800,940 | 4 | One CTA; native `marqueeLeft` scroll |

Build in Xibo CMS using Library media tagged `exhibit:seagrass-for-manatees`.

## Insight card overview

| Card | Window | Title | Art asset |
| --- | --- | --- | --- |
| 1 | 0–6s | Food | `graphic-diet-seagrass` |
| 2 | 6–12s | Threat | `graphic-threat-meadow` |
| 3 | 12–18s | Hidden Fact | `graphic-fact-nursery` |
| 4 | 18–24s | How to Help | `graphic-help-protect` |

## Motion guidelines

- Zone A: **no transitions** — still for the full layout life.
- Zone B art/copy: **Fade** together every **6 seconds**.
- Zone C: Xibo native **marqueeLeft** (via `effect: tickerScroll` in timeline).
- Card/ticker band color is painted **inside** the text widget — no separate scrim images.
- Copy is plain text with real line breaks (`|` blocks) — no Markdown, no emoji.

## Deliverables

1. **Media asset checklist** — [`../media/ASSETS.md`](../media/ASSETS.md)
2. **Widget timeline script** — [`timeline.yaml`](timeline.yaml)
