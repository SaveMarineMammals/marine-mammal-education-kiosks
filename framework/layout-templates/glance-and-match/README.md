# Template: glance-and-match

## Intent

Tank-side identification layout for passing traffic. A **static** left hero lets
visitors match the screen to the animal in under 3 seconds. The right side pages
through a short insight loop (art above, opaque copy below), with a continuous
CTA ticker at the base of the right pane.

## Canvas

- 1920×1080 landscape
- Typical insight cycle: 24–28s (4 cards × 5–7s)
- CMS **hold** (`layoutHoldSeconds`, default 3600): static regions stay up while
  insight playlists repeat — avoids a black flash from reloading the layout every cycle

## Regions (Glance & Match anatomy)

| Region | Zone | Size / position | z-order | Content |
| --- | --- | --- | --- | --- |
| `insights-bg` | B/C | 1120×1080 @ 800,0 | 0 | Right-pane wash — visual separation from hero |
| `hero-bg` | A | 800×1080 @ 0,0 | 1 | Habitat wash sized to the pane (**cover / portrait asset** — no letterbox bars) |
| `hero-still` | A | ~720×740 @ 40,300 | 2 | Transparent ID still in the lower frame only |
| `hero-labels` | A | ~752×260 @ 24,24 | 3 | Common name, scientific name, metrics |
| `insights-art` | B | ~1040×440 @ 840,32 | 2 | Paging card graphics only |
| `insights-copy` | B | ~1040×280 @ 840,500 | 3 | Title/bullets with band color inside the text widget |
| `ticker` | C | 1120×140 @ 800,940 | 4 | Slim footer; one short CTA; native marqueeLeft |

Leave a clear **gap** between `insights-copy` bottom and `ticker` top so the two
text bands do not read as one cluttered stack. The CTA belongs only in the ticker
— do not repeat the same donate line inside the How to Help card.

## Motion

- Zone A: **100% static** — zero looping or rotation.
- Zone B: Fade art and copy together every 5–7s; max 3–4 cards. Use
  `transitionIn: none` on the first card and `transitionOut: none` on the last
  so the playlist wrap (card 4 → card 1) does not flash empty.
- Zone C: continuous ticker via native **marqueeLeft**; speed readable at a walking glance.
- No video required; motion comes from paging + ticker only.

## CMS notes

- Tag media with `exhibit:<slug>` plus role tags (`role:hero-id`, `role:insight-card`).
- Hero wash JPEG must match the hero pane aspect (e.g. **800×1080**) or be cover-cropped — never a 16:9 still centered in a tall pane (letterboxing).
- Hero / card stills should be **transparent PNGs**.
- Set timeline `durationSeconds` to one full insight cycle; set
  `layoutHoldSeconds` (typically **3600**) so the CMS layout hold is much longer.
  The publisher stretches single-widget regions (hero / wash / ticker) to the hold
  and lets multi-widget insight regions **repeat** until the hold ends.
- Do not animate or cycle Zone A assets.

## Copy rules

- Plain text for CMS text widgets (no Markdown `**`, no emoji).
- Short bullets; **≤12 words per bullet**; use literal `|` YAML blocks so line breaks survive.
- Kid-friendly reading level (~8 years); high contrast per `framework/standards/accessibility.md`.
- **Card-copy** band color must be painted **inside the text widget** HTML. Do
  **not** place a separate scrim image behind card copy — Xibo aspect-fits images
  to the region, so a mismatched aspect centers a floating box while text stays
  left-aligned.
- **Ticker** band color is the region `backgroundColor` (publisher sets `#0A2A3A`).
  Marquee HTML must be text-only — a full-size colored `width:100%` div scrolls as
  a panel and never finishes a pass before the layout reloads.
- Timeline must set `effect: tickerScroll`. The publisher maps that to Xibo
  native `effect=marqueeLeft` + `speed: 2`, with the CTA duplicated for a
  continuous crawl (CSS `@keyframes` do **not** run in Xibo text widgets on the
  Linux player).
- Keep CTA out of the How to Help card bullets when the ticker already carries it.