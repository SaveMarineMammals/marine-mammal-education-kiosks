# Asian Small-Clawed Otters

Tank-side Glance & Match kiosk for Asian small-clawed otters
(*Aonyx cinereus*). Static left hero for instant ID; right-side paging cards
for deeper facts; continuous CTA ticker.

## Learning goals

- Visitors can match the screen to the otter in the habitat in under 3 seconds.
- Visitors can name one food the otters find with their paws.
- Visitors can name one threat and one local action (donate to a wildlife group).

## Audience

General public; copy optimized for an **8-year-old** reading/comprehension level.

## Package layout

| Path | Purpose |
| --- | --- |
| [`copy/en.md`](copy/en.md) | Hero metrics, 4 insight cards, ticker CTA |
| [`layouts/README.md`](layouts/README.md) | Zone A/B/C geometry + CMS build notes |
| [`layouts/timeline.yaml`](layouts/timeline.yaml) | Widget timeline (second marks) |
| [`media/manifest.yaml`](media/manifest.yaml) | Library asset index |
| [`media/ASSETS.md`](media/ASSETS.md) | Media asset checklist |
| [`schedule/intent.yaml`](schedule/intent.yaml) | Display group / daypart intent |

## Call to action

Donate to your local wildlife conservation group.

## Sources

- Replace with curated scientific and institutional citations before `review`.
  (IUCN Red List: *Aonyx cinereus* — Vulnerable.)

## Notes for authors

- Images and sound under **2 MB each** go in `media/assets/` (committed); video / files ≥ 2 MB go to the media store via local `media/asian-small-clawed-otters/masters/` (gitignored).
- Record hashes and repo or store URIs in `media/manifest.yaml`.
- Typography: **Source Sans 3** (body) and **Fraunces** (display titles) per
  `framework/branding/tokens.json` — large, high-contrast, min ~28 px captions.
- Build the layout in CMS from template `glance-and-match`.
- Zone A must stay **100% static** — never cycle the hero ID panel.
