# Red Mangrove — The Walking Tree

Tank-side Glance & Match kiosk about red mangroves (*Rhizophora mangle*) —
“the walking tree” — and why their stilt roots, nurseries, and storm-buffering
matter for coasts and species like the Greater Caribbean manatee. Static left
hero for instant ID; right-side paging cards for deeper facts; continuous CTA
ticker.

## Learning goals

- Visitors can match the screen to a red mangrove (stilt roots) in under 3 seconds.
- Visitors can name one way roots help animals or coasts.
- Visitors can name one reason to protect mangroves (storms, nursery, carbon, or manatees).

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

Protect mangroves — coasts, nurseries, and manatees need them.

## Interactive idea (facilitator / optional overlay)

Can you spot how many animals are hiding in the roots?

(Also surfaced as a kid prompt on the Fish Nursery card.)

## Sources

- Replace with curated scientific and institutional citations before `review`.
  (*Rhizophora mangle* — red mangrove; prop roots, viviparous propagules, coastal
  protection, nursery habitat, blue carbon. Linked species: Greater Caribbean /
  West Indian manatee *Trichechus manatus*.)

## Notes for authors

- Images and sound under **2 MB each** go in `media/assets/` (committed); video / files ≥ 2 MB go to the media store via local `media/red-mangrove/masters/` (gitignored).
- Record hashes and repo or store URIs in `media/manifest.yaml`.
- Typography: **Source Sans 3** (body) and **Fraunces** (display titles) per
  `framework/branding/tokens.json` — large, high-contrast, min ~28 px captions.
- Build the layout in CMS from template `glance-and-match`.
- Zone A must stay **100% static** — never cycle the hero ID panel.
