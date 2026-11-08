# Xibo CMS

## Role

Central **Xibo CMS Open Source Edition** hosts the media library, layouts, playlists, and schedules. Players connect to this CMS over the network.

## Install notes

- Prefer the official Docker-based CMS deployment for easier upgrades.
- Full host procedure (Ubuntu Server on a mini PC): [`../runbooks/install-cms-host.md`](../runbooks/install-cms-host.md).
- Host bootstrap scripts: [`scripts/`](scripts/).
- **Facility Tailscale** (CMS + players): [`../runbooks/facility-tailscale.md`](../runbooks/facility-tailscale.md) and [`scripts/install-tailscale.sh`](scripts/install-tailscale.sh).
- **Content sync** (Git `main` → Library + layouts): [`../runbooks/cms-content-sync.md`](../runbooks/cms-content-sync.md) and [`scripts/deploy-cms-sync.sh`](scripts/deploy-cms-sync.sh).
- Configure PHP/CMS upload limits high enough for layout ZIPs and large library media (see Xibo post-install guidance).
- Store CMS admin credentials and API keys in environment variables or a secrets manager — **never commit them**.

Suggested env files (local only, gitignored):

```text
# Developer machine (.env from repo root .env.example)
XIBO_CMS_URL=https://server.kiosks.local.belize.savemarinemammals.com
XIBO_CLIENT_ID=
XIBO_CLIENT_SECRET=
MEDIA_STORE_URI=file:///mnt/media-store

# CMS host production (/etc/mmek/cms-sync.env from cms-sync.env.example)
# Prefer loopback to cms-web after TLS (Caddy owns :80/:443):
# XIBO_CMS_URL=http://127.0.0.1:8080
```

TLS (Caddy + Let's Encrypt DNS-01 / Route 53):
[`caddy/README.md`](caddy/README.md), [`scripts/enable-cms-tls.sh`](scripts/enable-cms-tls.sh),
and [`../runbooks/install-cms-host.md`](../runbooks/install-cms-host.md) §8.

For an **ephemeral local CMS + headless player** used in CI-style visual QA, see [../qa/](../qa/) (`docker-compose.test.yml` + `run_qa_pipeline.py`).

## Folder taxonomy

Mirror Git exhibit slugs in the Library:

```text
Library/
  exhibits/
    humpback-migration/
    sea-otter-kelp/
    ...
  framework/
    branding/
    playlists/
```

## Tag conventions

| Tag | Meaning |
| --- | --- |
| `exhibit:<slug>` | Belongs to an exhibit package |
| `role:<role>` | hero-video, hero-still, audio-bed, etc. |
| `playlist:<name>` | Shared playlist media |
| `mmek:managed` | Created/updated by `tools/sync_cms.py` |
| `sha256:<43 hex digits>` | Content-hash prefix for media reuse. Xibo tags are limited to 50 characters, so this is `sha256:` plus the first 43 digits of the manifest digest. Sync still checks file bytes against the full sha256 before upload. |

## Sync flow (repo / media store → Library + layouts)

1. Author sets `status: published` and merges to `main`.
2. CMS host agent runs `tools/sync_cms.py --all-published` (Actions on label `mmek-cms` and/or daily systemd timer).
3. Media lands under `exhibits/<slug>` with manifest tags; layout **`mmek-<slug>`** is created once then updated in place.
4. **Operators** bind that layout’s campaign to **display groups** in the CMS UI. Sync never edits schedules.

See [media-sync.md](media-sync.md) and [cms-content-sync.md](../runbooks/cms-content-sync.md).
