# Media asset checklist — Humpback Migration

All scene masters are committed under `media/assets/` (**under 2 MB each**).
**No video files.** Sync into Xibo Library folder `exhibits/humpback-migration`.

## Typography (CMS text widgets)

| Use | Font | Size / weight | Notes |
| --- | --- | --- | --- |
| Scene body | Source Sans 3 | ≥ 36 px, semi-bold (600) | Short sentences; max ~2 lines preferred |
| Optional scene title | Fraunces | ≥ 48 px, bold | Only if not already in the body line |
| Scrim | — | — | Dark semi-opaque bar behind text (`#0B3D5C` @ ~70% opacity) |

## Background textures (`role: scene-bg`, 1920×1080 JPEG)

| Asset id | Filename | Scene | Status |
| --- | --- | --- | --- |
| `bg-migration-map` | `bg-migration-map.jpg` | 1 | Present — illustrated polar→tropics ocean map |
| `bg-polar-seas` | `bg-polar-seas.jpg` | 2 | Present — icy polar waters |
| `bg-tropical-ocean` | `bg-tropical-ocean.jpg` | 3 | Present — sunny tropical sea |
| `bg-nutrient-depths` | `bg-nutrient-depths.jpg` | 4 | Present — underwater light shafts |
| `bg-open-ocean-muted` | `bg-open-ocean-muted.jpg` | 5 | Present — calm muted horizon |
| `bg-hero-splash` | `bg-hero-splash.jpg` | 6 | Present — bright splash surface |

## Transparent PNG graphics (`role: scene-graphic`)

| Asset id | Filename | Scene | Status |
| --- | --- | --- | --- |
| `graphic-migration-route` | `graphic-migration-route.png` | 1 | Present — dotted accent route overlay |
| `graphic-whale-swim` | `graphic-whale-swim.png` | 1 | Present — side-view humpback |
| `graphic-krill-school` | `graphic-krill-school.png` | 2 | Present — krill / fish swarm |
| `graphic-mother-calf` | `graphic-mother-calf.png` | 3 | Present — mother + calf |
| `graphic-food-web` | `graphic-food-web.png` | 4 | Present — nutrients / plants / oxygen |
| `graphic-ship-silhouette` | `graphic-ship-silhouette.png` | 5 | Present — friendly freighter icon |
| `graphic-net-warning` | `graphic-net-warning.png` | 5 | Present — net + plastic cue |
| `graphic-whale-tail` | `graphic-whale-tail.png` | 6 | Present — fluke / splash CTA |

## Accent overlay (`role: accent-loop`)

| Asset id | Filename | Status |
| --- | --- | --- |
| `accent-bubbles-loop` | `accent-bubbles-loop.zip` (+ loose `.html`) | Present — rising bubbles HTML package |

## Preview thumbs

Tiny JPEGs under `media/previews/` referenced by `preview:` in `manifest.yaml`.

## Explicitly excluded

- Any `.mp4` / `.webm` / `.mov` hero or B-roll
- Dense paragraph text panels
- Frightening hazard imagery (Scene 5 stays clean and kid-safe)
