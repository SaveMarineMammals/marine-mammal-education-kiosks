# Framework

Shared components used across exhibits. **Rule:** if two or more exhibits need it, it belongs here.

| Path | Purpose |
| --- | --- |
| [`branding/`](branding/) | Logos, fonts, color tokens, attribution boilerplate |
| [`layout-templates/`](layout-templates/) | Reusable Xibo layout recipes |
| [`preview/`](preview/) | Local static mockups of branding + templates |
| [`widgets/`](widgets/) | Custom Xibo module/template XML sources |
| [`playlists/`](playlists/) | Shared attract / idle / interstitial definitions |
| [`standards/`](standards/) | Resolution, duration, accessibility, checklists |

## Local preview

```powershell
python tools/serve_preview.py
```

Then open [http://localhost:4173/framework/preview/](http://localhost:4173/framework/preview/) (server must be started from the repo root).
