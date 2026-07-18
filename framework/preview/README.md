# Local layout & branding preview

Static mockups of `framework/branding` tokens and the three layout templates at **1920×1080** (scaled in the browser).

This is a **design aid** for contrast, type size, safe margins, and composition. It does **not** replace Xibo CMS or player playback.

## Run

From the **repository root**:

```powershell
cd C:\Users\jeff\Projects\marine-mammal-education-kiosks
python tools/serve_preview.py
```

Open [http://localhost:4173/framework/preview/](http://localhost:4173/framework/preview/)

You should see color swatches, a type specimen, and three template stages. Status text should say tokens loaded.

(`python -m http.server 4173` from the repo root also works.)

## What it loads

| Source | Used for |
| --- | --- |
| `framework/branding/tokens.json` | CSS variables, swatches, caption size |
| `exhibits/humpback-migration/copy/en.md` | Title / caption / CTA on mockups |
| `framework/preview/assets/ocean-placeholder.svg` | Stand-in for Library media |

## Notes

- Opening `index.html` via `file://` will usually fail token/copy fetches — use the HTTP server above.
- Safe-margin overlays use the 96px inset from `framework/standards/resolution.md`.
- Interactive buttons in the HTML template mock are cosmetic only.
