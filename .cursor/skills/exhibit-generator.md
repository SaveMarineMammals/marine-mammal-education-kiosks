---
name: exhibit-generator
description: >-
  Create a new Glance & Match educational exhibit package under exhibits/<slug>/
  for marine-mammal-education-kiosks (Xibo kiosk layouts, copy, media, catalog).
  Use when the user asks to generate, scaffold, or author a new exhibit module.
---

# Exhibit generator (Glance & Match)

You are a content architect for SaveMarineMammals/marine-mammal-education-kiosks.
Create a complete exhibit package that the QA pipeline can publish — not just copy
notes.

## Before generating — ask for these details

Ask for the following before creating files (if not already provided):

1. The target marine mammal species or conservation theme.
2. The primary call-to-action (CTA) or conservation group we are supporting.

Then generate the full package (see Checklist below).

## Package contract

Follow `docs/exhibit-authoring.md`. Create:

```text
exhibits/<kebab-slug>/
  exhibit.yaml
  README.md
  copy/en.md
  layouts/README.md
  layouts/timeline.yaml
  media/manifest.yaml
  media/ASSETS.md
  media/assets/          # images/sound under 2 MB each
  media/previews/        # tiny thumbs
  schedule/intent.yaml
```

Also:

- Register the exhibit in `exhibits/_catalog.yaml` and list it in `exhibits/README.md`.
- Set `layoutTemplate: glance-and-match` in `exhibit.yaml`.
- Use template docs at `framework/layout-templates/glance-and-match/`.
- Prefer mirroring `exhibits/asian-small-clawed-otters/` (Glance & Match reference).
  Use `exhibits/humpback-migration/` only when the template is layered stills.

## Glance & Match anatomy

Use these **exact region ids** in `layouts/timeline.yaml` so `ops/qa/exhibit_layout.py`
can publish geometry (do **not** invent `background` / `midground` names for this template):

| Region | Zone | Geometry (1920x1080) | Purpose |
| --- | --- | --- | --- |
| `insights-bg` | B/C | 1120x1080 @ 800,0 | Right-pane wash — separates from hero |
| `hero-bg` | A | 800x1080 @ 0,0 | Habitat wash filling the left pane (no letterbox) |
| `hero-still` | A | ~720x740 @ 40,300 | Transparent ID still in the **lower** frame only |
| `hero-labels` | A | ~752x260 @ 24,24 | Common name, scientific name, metrics |
| `insights-art` | B | ~1040x440 @ 840,32 | Paging card **graphics only** |
| `insights-copy` | B | ~1040x280 @ 840,500 | Card title + bullets (band color **inside** text widget) |
| `ticker` | C | 1120x140 @ 800,940 | Slim footer; one short CTA; native marquee |

Leave a clear **vertical gap** between `insights-art` and `insights-copy`, and a
second gap between `insights-copy` and `ticker`, so card copy and CTA never sit
as two adjacent text blocks.

Set `template: glance-and-match` and `durationSeconds` to one full insight cycle
(typically **24s** = 4 x 6s).

### Zone A — Static hero (Tier 1)

- **100% static** — zero looping, rotation, or fade-cycling of the ID panel.
- Large common name + scientific name; size + conservation status metrics.
- High-visibility identifier for tank match in under **3 seconds**.
- Split the hero into **`hero-bg` + `hero-still` + `hero-labels`** (do not put wash,
  still, and labels in one tall region).
- `hero-bg` JPEG must be **cover-cropped to the pane aspect** (800x1080). A 16:9
  still centered in a tall region creates black letterbox bars above/below — that
  is unpolished and must not ship.
- Hero still must be a **transparent PNG** over the wash. Never ship a solid black
  (or solid color) matte behind the animal.

### Zone B — Paging insights (Tier 2)

- **3–4 cards**, **5–7 seconds** each (prefer **6s**).
- Default card set: Diet, Threat, Hidden Fact, How to Help (adjust titles to theme).
- **Split art and copy into separate regions** (`insights-art` + `insights-copy`).
  Never stack card text over the illustration in the same region.
- Fade art and copy **together** on the same card window.
- Right pane must have `insights-bg` (teal/habitat wash with a soft left-edge
  divider) so Zone A and Zone B are visually separated. Do not rely on the default
  black player canvas.

### Zone C — Ticker (Tier 3)

- Slim footer band on the **right pane**, separated by a clear gap from
  `insights-copy` (pane wash should show between the two text bands).
- **One short CTA only** (the user-provided action). Do not concatenate multiple
  slogans with `|` — that dumps too many words on screen at once.
- Keep CTA out of the How to Help card bullets when the ticker already carries it.

## Text bands and player motion (critical)

These rules come from live Xibo Linux Player QA failures. Follow them exactly.

### Text + background must be one widget

- Paint card-copy and ticker band color **inside the text widget HTML**
  (e.g. `background:#0A2A3A` on the content div).
- Do **not** place a separate scrim/image behind the text.
- Why: Xibo aspect-fits images to the region. A scrim whose pixel aspect does not
  match the region is scaled and **centered**, while text stays left-aligned —
  the dark “highlight” drifts away from the glyphs.

### Ticker must use native marquee

- Timeline sets `effect: tickerScroll`.
- QA publisher (`ops/qa/run_qa_pipeline.py` `add_text_widget`) must map that to
  Xibo native **`effect=marqueeLeft`** with a slow **`speed`** (e.g. `1`).
- Do **not** rely on CSS `@keyframes` / HTML marquee animations inside text HTML —
  they stay **frozen** on the Linux player even when Chromium preview scrolls.
- CTA copy should be a single short sentence (not a pipe-joined slogan list).

### Timeline copy must survive the player

- Use YAML literal blocks (`copy: |`) so line breaks survive. Never use folded
  scalars (`copy: >`) for multi-line kiosk text — they collapse to one long line.
- Plain text only in timeline fields: no Markdown `**bold**`, no emoji, no fancy
  bullets (`•` `·`). Use ASCII `-` list markers.
- Xibo text widgets escape/do not render Markdown; symbols often become junk glyphs.

## Copy rules (CMS-safe)

Xibo text widgets **do not render Markdown**. Author-facing docs may use Markdown;
**timeline `copy:` fields must be plain text**.

Do:

- Short bullets, **<=12 words per bullet**.
- Clear blank lines between title and bullets.
- Kid-friendly ~8-year-old reading level.

Author notes in `copy/en.md` may mention emphasis for humans; the timeline is source
of truth for what the player shows.

## Media rules

Follow `.cursor/rules/media-policy.mdc` and `docs/architecture.md` (Media strategy):

- Every committed image/sound **under 2 MB**; record `sha256`, `mime`, `bytes`,
  repo-relative `uri` in `media/manifest.yaml`.
- Hero ID and card icons: **transparent PNG** (key out solid black mattes after
  generation if needed).
- Required washes:
  - Left `hero-bg` habitat JPEG at **pane pixel size** (800x1080) or cover-cropped
  - Right `insights-bg` pane JPEG
  - Card/ticker band color via text-widget HTML (not separate scrim images)
- Preview thumbs under `media/previews/`; list pending vs present in `media/ASSETS.md`.
- No video on Zone A; no frightening hazard art on Threat cards.

When generating media in-session: write files under `exhibits/<slug>/media/assets/`,
update hashes in the manifest, and bind every asset from `layouts/timeline.yaml`.

## QA pipeline compatibility (mandatory)

`ops/qa/exhibit_layout.py` only creates regions it knows. For Glance & Match:

- Region names must match the table above (`hero-bg`, `hero-still`, `hero-labels`,
  `insights-bg`, `insights-art`, `insights-copy`, `ticker`).
- Overlapping widgets in one zone are split into overlay playlists automatically;
  still keep art and copy in **different** regions for layout clarity.
- After generation, a QA run should report **non-empty `regions`** and a non-black
  frame. Empty `regions: []` means the timeline used unsupported region names.
- Visual QA checks:
  - No letterbox bars on the hero
  - Text band background aligned with glyphs (not a floating box)
  - CTA crawls in the recorded video (native marquee), not a truncated static line

Reference: `ops/qa/README.md`, `framework/layout-templates/glance-and-match/README.md`,
`exhibits/asian-small-clawed-otters/` (working reference package).

## Tier / content checklist (Glance & Match)

- [ ] Tier 1 permanent hero (`hero-bg` + `hero-still` + `hero-labels`)
- [ ] Hero wash is pane-aspect / cover-cropped (no letterbox bars)
- [ ] Tier 2: 3–4 paging cards (art + copy regions, 5–7s each, clear gaps)
- [ ] Tier 3: one short CTA with `effect: tickerScroll` → native `marqueeLeft`
- [ ] Text band color inside text widgets (no separate scrim images)
- [ ] `insights-bg` separation between left and right
- [ ] Transparent hero/card PNGs; habitat + pane JPEG washes
- [ ] Plain CMS copy with `|` line breaks; no Markdown/emoji in timeline
- [ ] Catalog + `exhibit.yaml` + schedule intent + media manifest hashes

## Anti-patterns (do not repeat)

1. Publishing only `background`/`midground`/`text`/`accent` for a Glance & Match
   exhibit — QA will publish **zero regions** and capture a black frame.
2. Solid black PNG mattes that erase habitat washes.
3. Markdown/emoji in timeline copy.
4. Folded YAML (`>`) multi-line copy that becomes one unreadable block.
5. Card text drawn on top of the insight illustration.
6. Flat black canvas with no left/right pane separation.
7. 16:9 (or other mismatched) hero wash centered in a tall pane — black bars
   above/below.
8. Semi-transparent copy over a busy pane wash — text flows into the image.
9. Single combined `hero` region holding wash + still + labels (letterboxing and
   stacking bugs).
10. Packing multiple CTA slogans into the ticker (wall of text when static).
11. Stacking `insights-copy` directly against `ticker` with no gap — two competing
    text blocks.
12. CSS `@keyframes` / HTML marquee inside text widgets — frozen on the Linux
    player; use Xibo `marqueeLeft` instead.
13. Separate scrim **images** behind text — aspect-fit centers the box while text
    stays left-aligned (misaligned highlight).
14. Repeating the donate CTA in both How to Help bullets and the ticker.
