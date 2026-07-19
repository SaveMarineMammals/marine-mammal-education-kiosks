# Template: glance-and-match

## Intent

Tank-side identification layout for passing traffic. A **static** left hero lets
visitors match the screen to the animal in under 3 seconds. The right side pages
through a short insight loop (art above, opaque copy below), with a continuous
CTA ticker at the base of the right pane.

## Canvas

- 1920×1080 landscape
- Typical insight cycle: 24–28s (4 cards × 5–7s); layout loops continuously

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
- Zone B: Fade art and copy together every 5–7s; max 3–4 cards.
- Zone C: continuous ticker via native **marqueeLeft**; speed readable at a walking glance.
- No video required; motion comes from paging + ticker only.

## CMS notes

- Tag media with `exhibit:<slug>` plus role tags (`role:hero-id`, `role:insight-card`).
- Hero wash JPEG must match the hero pane aspect (e.g. **800×1080**) or be cover-cropped — never a 16:9 still centered in a tall pane (letterboxing).
- Hero / card stills should be **transparent PNGs**.
- Set layout duration to one full insight cycle; playlist should loop the layout.
- Do not animate or cycle Zone A assets.

## Copy rules

- Plain text for CMS text widgets (no Markdown `**`, no emoji).
- Short bullets; **≤12 words per bullet**; use literal `|` YAML blocks so line breaks survive.
- Kid-friendly reading level (~8 years); high contrast per `framework/standards/accessibility.md`.
- Copy-band and ticker backgrounds must be painted **inside the text widget**
  (HTML `background` / CMS background). Do **not** place a separate scrim image
  behind the text — Xibo aspect-fits images to the region, so a mismatched aspect
  ratio centers a floating box while text stays left-aligned.
- Timeline must set `effect: tickerScroll`. The QA publisher maps that to Xibo
  native `effect=marqueeLeft` + slow `speed` (CSS `@keyframes` do **not** run in
  Xibo text widgets on the Linux player).
- Keep CTA out of the How to Help card bullets when the ticker already carries it.