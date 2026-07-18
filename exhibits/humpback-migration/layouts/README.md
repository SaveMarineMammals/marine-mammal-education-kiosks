# Layout recipe: Humpback Migration

**Template:** `framework/layout-templates/full-bleed-video`

## Canvas

- Resolution: 1920×1080
- Orientation: landscape

## Regions

1. **Full-bleed video** — asset `hero-video` from `media/manifest.yaml`
2. **Lower-third caption** (optional overlay) — text from `copy/en.md` short caption

## Notes

Build the layout in Xibo CMS using Library media tagged `exhibit:humpback-migration`.
Do not commit export ZIPs that embed full library media; place those under `dist/` if needed for transfer.
