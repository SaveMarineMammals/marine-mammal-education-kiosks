# Ephemeral visual QA pipeline (Xibo CMS + headless player)

Isolated Docker Compose stack that boots Xibo CMS (web, MySQL, XMR), a headless
**Xibo Linux Player** on Xvfb at **1920×1080**, publishes the exhibit layout via
the REST API, and records the live player framebuffer.

**Default path:** when `exhibits/<slug>/layouts/timeline.yaml` exists, the
pipeline uploads local assets, builds a multi-region layout in CMS from the
timeline template (`layered-stills-loop` or `glance-and-match`), publishes it,
schedules it to the QA display, and captures `scrot` + `ffmpeg` from the snap
player.

**Escape hatch:** `--preview-only` (or `QA_USE_TIMELINE_PREVIEW=1`) renders a
Chromium timeline preview instead of recording the Xibo player.

**CI (no Docker):** `ci_timeline_preview.py` renders the Chromium timeline and
captures a still via Playwright — used by the `Timeline preview` workflow.
**CI (full player):** GitHub Actions workflow `QA player capture` runs this
pipeline on `workflow_dispatch`, nightly, or PRs labeled `qa-player` (not a
required merge check).

## Layout

| Path | Purpose |
| --- | --- |
| `Dockerfile.player` | Ubuntu + Xvfb/scrot/ffmpeg + Chrome + extracted Xibo Linux Player snap |
| `download_player_snap.py` | Resolves/downloads the player snap during image build |
| `entrypoint.sh` | Starts `:99` Xvfb + Xibo player; Chromium/feh only when `QA_USE_TIMELINE_PREVIEW=1` |
| `exhibit_layout.py` | Builds multi-region layouts from `timeline.yaml` |
| `timeline_preview/` | Optional Chromium renderer for `--preview-only` |
| `docker-compose.test.yml` | CMS web/db/xmr/memcached/quickchart + `kiosk-player` |
| `config.env.example` | Deterministic local env (copy to `config.env`) |
| `run_qa_pipeline.py` | End-to-end orchestration |
| `requirements.txt` | `requests` + `Pillow` + `PyYAML` |
| `fixtures/` | Sample upload asset (auto-generated if missing) |
| `artifacts/` | Host-side captures + `qa-report.json` (gitignored) |

## Prerequisites

- Docker Engine + Compose v2
- Python 3.10+
- Enough RAM/disk for CMS images (~2–4 GB)

## Quick start

### WSL / Linux

System Python often has no `pip`. Use a local venv (no sudo required):

```bash
cd ops/qa
cp config.env.example config.env

python3 -m venv --without-pip .venv
curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
.venv/bin/python /tmp/get-pip.py
.venv/bin/pip install -r requirements.txt

.venv/bin/python run_qa_pipeline.py -v
```

Or, if you prefer apt packages (needs sudo once):

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_qa_pipeline.py -v
```

### Windows PowerShell

```powershell
cd ops\qa
copy config.env.example config.env
python -m pip install -r requirements.txt
python run_qa_pipeline.py -v
```

The script will:

1. `docker compose up -d --build` (includes `cms-xmr` Message Relay)
2. Wait for MySQL health + CMS OAuth endpoint
3. Seed CMS `XMR_ADDRESS` / `XMR_PUB_ADDRESS` for the compose network (`tcp://cms-xmr:…`)
4. Obtain an OAuth2 **client_credentials** token (auto-bootstraps an Application if `XIBO_CLIENT_ID` / `XIBO_CLIENT_SECRET` are empty)
5. Upload timeline-referenced local assets; create multi-region layout; publish
6. Authorise the QA display, set default layout, schedule / `changeLayout`, and `collectNow` over XMR
7. Restart the player for a clean XMDS collect, wait for library sync, then `scrot` + `ffmpeg` (`--duration`)
8. Copy artifacts to `ops/qa/artifacts/`
9. Verify 1920×1080 bounds, non-black frame, and pixel variance
10. `docker compose down -v` (unless `--keep-stack`)

## Useful flags

```bash
# Defaults: --exhibit humpback-migration --duration 30 (Xibo player capture)
.venv/bin/python run_qa_pipeline.py -v

# Fast iteration on a warm stack (recommended while debugging):
# - skips player image rebuild
# - keeps stack up
# - short XMR waits + library poll instead of fixed 90s sleep
# - PNG-only (add --record-video for MP4)
.venv/bin/python run_qa_pipeline.py -v --fast --skip-up

# After changing Dockerfile.player / entrypoint.sh / shim:
.venv/bin/python run_qa_pipeline.py -v --fast --skip-up --rebuild-player

.venv/bin/python run_qa_pipeline.py -v --exhibit humpback-migration --duration 30
.venv/bin/python run_qa_pipeline.py -v --exhibit humpback-migration --duration 90
.venv/bin/python run_qa_pipeline.py --preview-only -v   # Chromium timeline preview
.venv/bin/python run_qa_pipeline.py --keep-stack
.venv/bin/python run_qa_pipeline.py --skip-up --keep-stack
.venv/bin/python run_qa_pipeline.py --media ../../framework/preview/assets/ocean-placeholder.svg
.venv/bin/python run_qa_pipeline.py --verify-only artifacts/frame-....png
```

Without `--media`, the pipeline resolves the first local `scene-bg` image from
`exhibits/<slug>/media/manifest.yaml` (fallback single-image layout / feh still).
When `layouts/timeline.yaml` is present, the default path publishes that full
exhibit to CMS and records the Xibo player. `--duration` controls ffmpeg `-t`
(default 5s in `--fast`, 30s otherwise).

Report field `renderer` is `xibo-player` (default) or `timeline-preview` (`--preview-only`).

## Manual compose

```powershell
docker compose -f docker-compose.test.yml --env-file config.env up -d --build
docker compose -f docker-compose.test.yml --env-file config.env down -v --remove-orphans
```

CMS UI (ephemeral): [http://127.0.0.1:8080](http://127.0.0.1:8080) — default `xibo_admin` / `password`.

## Credentials

Do **not** hardcode secrets. Use `config.env` (gitignored) or the repo-root `.env`:

| Variable | Role |
| --- | --- |
| `MYSQL_PASSWORD` | CMS DB user password |
| `XIBO_CMS_URL` | Host URL for the orchestrator |
| `XIBO_CLIENT_ID` / `XIBO_CLIENT_SECRET` | OAuth2 application |
| `XIBO_ADMIN_USER` / `XIBO_ADMIN_PASSWORD` | Used only to bootstrap an Application when client creds are empty |
| `XIBO_CMS_KEY` | Player registration key (discovered from settings when empty) |
| `XIBO_DISPLAY_NAME` | Expected player display name |
| `XIBO_XMR_ADDRESS` | Player/CMS public XMR (`tcp://cms-xmr:9505` on qa-net) |
| `XIBO_XMR_PRIVATE_ADDRESS` | CMS→XMR HTTP API (`http://cms-xmr:8081`; CMS 4.2+) |
| `QA_EXHIBIT_SLUG` | Exhibit under `exhibits/` (default `humpback-migration`) |
| `QA_RECORD_DURATION` | Seconds of MP4 to capture (default `30`) |
| `QA_MEDIA_PATH` | Optional media override (skips manifest resolution) |
| `QA_USE_TIMELINE_PREVIEW` | `1` to force Chromium preview (same as `--preview-only`) |
| `QA_SKIP_HTML_PACKAGES` | `1` (default in headless player mode) skips `html-package` widgets that crash WebKitGTK under Xvfb; set `0` or pass `--include-html-packages` to keep them |
| `QA_IMAGE_ONLY_LAYOUT` | `1` or `--image-only-layout` publishes a single background image region (paint-crash bisect) |

## Headless player GL / WebKit

The extracted snap player under Xvfb uses **snap Mesa software GL only**:

- `LIBGL_ALWAYS_SOFTWARE=1`, `GALLIUM_DRIVER=llvmpipe`
- `LIBGL_DRIVERS_PATH=${SNAP}/usr/lib/x86_64-linux-gnu/dri` (snap Mesa; host DRI stays intact for Xvfb GLX)
- Xvfb started with `+extension GLX +render -noreset`
- Snap-first `LD_LIBRARY_PATH` (host-first is known-fatal)

WebKitGTK defaults for HTML packages: `WEBKIT_DISABLE_COMPOSITING_MODE=1`, `WEBKIT_FORCE_COMPOSITING_MODE=0`. When HTML still SIGSEGVs in `RegionImpl::start()`, headless QA omits those widgets so image+text regions still validate.

After XMR `changeLayout`, the pipeline waits until the **player process** stays alive before `scrot` (avoids black Xvfb-only frames while the supervisor restarts).

Keep-stack runs clear prior CMS schedule events for the display group before scheduling the new layout, so stale HTML-package layouts cannot crash `RegionImpl::start()` with an empty media list.

## Paths (WSL / Docker Desktop)

Host scripts use **POSIX repo-relative** URIs from manifests (`exhibits/<slug>/…`). Shared helpers live in `pathutil.py`:

- `resolve_manifest_path` — never treats `C:\…` fragments as relative paths under Linux/WSL
- `to_docker_path` — converts `/mnt/c/…` → `C:\…` only when the Docker CLI is Windows `docker.exe`

## Capture internals

Inside `xibo-qa-kiosk-player`:

```bash
export DISPLAY=:99
scrot -z /artifacts/frame.png
ffmpeg -f x11grab -video_size 1920x1080 -i :99 -t 5 /artifacts/clip.mp4
```

## Notes

- First player image build downloads the `xibo-player` snap and extracts it with `unsquashfs` (no snapd daemon at runtime).
- The player container runs `privileged` because extracted snap runtimes expect broad device access under Xvfb.
- Fresh CMS bootstrap can take several minutes; the orchestrator polls until `/api/authorize/access_token` responds.
- The stack always includes `cms-xmr` (Xibo Message Relay). The pipeline seeds `XMR_ADDRESS` (`http://cms-xmr:8081`) / `XMR_PUB_ADDRESS` (`tcp://cms-xmr:9505`), authorises the display **before** the player's READY `RegisterDisplay` (CMS Soap5 only persists `xmrChannel` when licensed), then `collectNow` / `changeLayout` over XMR. Pipeline XMDS register is skipped once a display row exists so it cannot wipe `xmrChannel`.
- The player image includes `libxibo_qa_shim.so` (`LD_PRELOAD`) so snap 1.8-R6 applies `<settings>` XML correctly and empty `localLibrary` paths fall back to `/data/xibo-library`.
