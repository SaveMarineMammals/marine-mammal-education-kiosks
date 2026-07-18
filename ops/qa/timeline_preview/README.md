# Timeline → Chromium preview for ephemeral visual QA.

| Path | Role |
| --- | --- |
| `render_timeline.py` | Reads `layouts/timeline.yaml` + `media/manifest.yaml`, writes HTML |
| `player.css` / `player.js` | Stage layers, transitions, and clock |

Output defaults to `ops/qa/player-runtime/timeline-preview/` (bind-mounted into
the kiosk player container as `/var/lib/xibo-player/timeline-preview/`).
