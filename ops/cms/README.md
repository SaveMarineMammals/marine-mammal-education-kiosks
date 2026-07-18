# Xibo CMS

## Role

Central **Xibo CMS Open Source Edition** hosts the media library, layouts, playlists, and schedules. Players connect to this CMS over the network.

## Install notes

- Prefer the official Docker-based CMS deployment for easier upgrades.
- Configure PHP/CMS upload limits high enough for layout ZIPs and large library media (see Xibo post-install guidance).
- Store CMS admin credentials and API keys in environment variables or a secrets manager — **never commit them**.

Suggested env file (local only, gitignored):

```text
XIBO_CMS_URL=https://cms.example.local
XIBO_CLIENT_ID=
XIBO_CLIENT_SECRET=
MEDIA_STORE_URI=s3://exhibits/  # or file:// path to NAS mount
```

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
| `status:published` | Optional; CMS may also track via folders |

## Sync flow (repo / media store → Library)

1. Author updates `exhibits/<slug>/media/manifest.yaml` with `sha256` + `uri` (repo-relative for images/sound under 2 MB; store key for video / files ≥ 2 MB).
2. `tools/sync-media` (or manual upload) copies objects whose hashes are not yet in the Library.
3. Files land in `exhibits/<slug>/` with tags from the manifest.
4. Layout authors attach Library items; schedules bind campaigns to **display groups** (location/role names).

See [media-sync.md](media-sync.md) for the detailed procedure.
