# Winter the Dolphin

Tank-side Glance & Match kiosk for Winter, a rescued Atlantic bottlenose
dolphin (*Tursiops truncatus*). Static left hero for instant ID; right-side
paging cards on diet, threats, her prosthetic tail story, and ways to help;
continuous CTA for marine mammal rescue.

## Learning goals

- Visitors can recognize a bottlenose dolphin on the screen in under 3 seconds.
- Visitors can name one food dolphins eat and one threat they face in the wild.
- Visitors know Winter was rescued and learn one reason rehabilitation centers matter.

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

Support marine mammal rescue and rehabilitation near you.

## Sources

- Replace with curated scientific and institutional citations before `review`.
  (Winter: Clearwater Marine Aquarium rescue story; *Tursiops truncatus* field guides.)

## Notes for authors

- Images and sound under **2 MB each** go in `media/assets/` (committed); video / files ≥ 2 MB go to the media store via local `media/winter-the-dolphin/masters/` (gitignored).
- Record hashes and repo or store URIs in `media/manifest.yaml`.
- Typography: **Source Sans 3** (body) and **Fraunces** (display titles) per
  `framework/branding/tokens.json` — large, high-contrast, min ~28 px captions.
- Build the layout in CMS from template `glance-and-match`.
- Zone A must stay **100% static** — never cycle the hero ID panel.