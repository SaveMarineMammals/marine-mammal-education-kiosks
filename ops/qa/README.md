# Ephemeral visual QA pipeline (Xibo CMS + headless player)

Isolated Docker Compose stack that boots Xibo CMS (web, MySQL, XMR), a headless
player container on Xvfb at **1920×1080**, injects media via the REST API, and
captures the framebuffer.

**Default visual path (hybrid):** when `exhibits/<slug>/layouts/timeline.yaml`
exists, the pipeline renders a Chromium **timeline preview** (layered stills,
transitions, captions) and records that. This is intentional — clips show scene
changes without requiring a fully stable Xibo Linux Player under Docker.

**Follow-up (not yet):** build the real multi-region Xibo layout from the
timeline via the CMS API and capture the snap player once XMR/`xmrChannel` is
reliable.

## Layout

| Path | Purpose |
| --- | --- |
| `Dockerfile.player` | Ubuntu + Xvfb/scrot/ffmpeg + Chrome + extracted Xibo Linux Player snap |
| `download_player_snap.py` | Resolves/downloads the player snap during image build |
| `entrypoint.sh` | Starts `:99` Xvfb; prefers Chromium timeline preview, then feh, then Xibo player |
| `timeline_preview/` | Renders `layouts/timeline.yaml` → HTML for Chromium |
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

1. `docker compose up -d --build`
2. Wait for MySQL health + CMS OAuth endpoint
3. Obtain an OAuth2 **client_credentials** token (auto-bootstraps an Application if `XIBO_CLIENT_ID` / `XIBO_CLIENT_SECRET` are empty)
4. Render `layouts/timeline.yaml` into `player-runtime/timeline-preview/` (Chromium)
5. Upload exhibit media (or `--media` override), create/checkout/publish a layout, assign media
6. Authorise the QA display, schedule / `changeLayout`, and `collectNow` over XMR
7. Restart the player so the timeline clock starts at t≈0, then `scrot` + `ffmpeg` (`--duration`)
8. Copy artifacts to `ops/qa/artifacts/`
9. Verify 1920×1080 bounds, non-black frame, and pixel variance
10. `docker compose down -v` (unless `--keep-stack`)

## Useful flags

```bash
# Defaults: --exhibit humpback-migration --duration 30
.venv/bin/python run_qa_pipeline.py -v

.venv/bin/python run_qa_pipeline.py -v --exhibit humpback-migration --duration 30
.venv/bin/python run_qa_pipeline.py -v --exhibit humpback-migration --duration 90
.venv/bin/python run_qa_pipeline.py --keep-stack
.venv/bin/python run_qa_pipeline.py --skip-up --keep-stack
.venv/bin/python run_qa_pipeline.py --media ../../framework/preview/assets/ocean-placeholder.svg
.venv/bin/python run_qa_pipeline.py --verify-only artifacts/frame-....png
```

Without `--media`, the pipeline resolves the first local `scene-bg` image from
`exhibits/<slug>/media/manifest.yaml` (used for CMS upload + static feh fallback).
When `layouts/timeline.yaml` is present, Chromium plays that timeline for the
recording. `--duration` controls both the preview clock window and ffmpeg `-t`.

Report field `renderer` is `timeline-preview` or `static-fallback`.

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
| `QA_EXHIBIT_SLUG` | Exhibit under `exhibits/` (default `humpback-migration`) |
| `QA_RECORD_DURATION` | Seconds of MP4 to capture (default `30`) |
| `QA_MEDIA_PATH` | Optional media override (skips manifest resolution) |

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
