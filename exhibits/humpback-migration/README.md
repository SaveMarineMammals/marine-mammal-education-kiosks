# Humpback Whale Migration

Interactive educational kiosk content for the humpback whale exhibit floor.
90-second looping story built from layered stills, text, and Xibo transitions
(**no video files**).

## Learning goals

- Visitors can say how far humpbacks travel and why (feed in cold seas, raise
  calves in warm seas).
- Visitors can explain one way whale migration helps the ocean food web / oxygen.
- Visitors can name one danger on the journey and one simple action they can take.

## Audience

General public; copy optimized for an **8-year-old** reading/comprehension level.

## Package layout

| Path | Purpose |
| --- | --- |
| [`copy/en.md`](copy/en.md) | Six scene texts + CTA |
| [`layouts/README.md`](layouts/README.md) | Xibo regions + CMS build notes |
| [`layouts/timeline.yaml`](layouts/timeline.yaml) | Widget timeline (second marks) |
| [`media/manifest.yaml`](media/manifest.yaml) | Library asset index |
| [`media/ASSETS.md`](media/ASSETS.md) | Media asset checklist |
| [`schedule/intent.yaml`](schedule/intent.yaml) | Display group / daypart intent |

## Sources

- Replace with curated scientific and institutional citations before `review`.

## Notes for authors

- Images and sound under **2 MB each** go in `media/assets/` (committed); video / files ≥ 2 MB go to the media store via local `media/humpback-migration/masters/` (gitignored).
- Record hashes and repo or store URIs in `media/manifest.yaml`.
- Typography: **Source Sans 3** (body) and **Fraunces** (display titles) per
  `framework/branding/tokens.json` — large, high-contrast, min ~28 px captions.
- Build the layout in CMS from template `layered-stills-loop`.
