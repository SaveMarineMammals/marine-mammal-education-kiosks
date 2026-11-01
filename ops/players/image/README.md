# Kiosk player golden image

Reproducible **Raspberry Pi OS arm64** image for NovoTouch kiosks: Lite base +
Arexibo + first-boot config from `/boot/firmware/kiosk.conf`.

Recipe version: see [`VERSION`](VERSION).

## Pipelines

| Workflow | Purpose |
| --- | --- |
| **Player image** (`.github/workflows/player-image.yml`) | Build `.img.xz` on demand (`workflow_dispatch`) or publish approved Releases on tags `player-image-v*` |
| **Kiosk config** (`.github/workflows/kiosk-config.yml`) | Generate per-kiosk `kiosk.conf` zip from Action inputs |

Physical mount / BOM: [`docs/facility-physical-setup.md`](../../../docs/facility-physical-setup.md).  
Player ops checklist: [`ops/players/README.md`](../README.md).

## Authentication (CMS key — not client certificates)

Xibo players use **XMDS** with a shared **CMS Key** plus a per-display hardware key.
Arexibo is configured with `--host` / `--key` (see `files/mmek-arexibo-start`).

**Client certificates cannot replace the CMS key.** OAuth client credentials are for
the CMS REST API only. Use HTTPS to the CMS (trust the server CA on the Pi).

## What’s in the image

- Raspberry Pi OS Lite (pi-gen `stage0`–`stage2`) + custom `stage-kiosk`
- **Arexibo** from [xiboplayer.org Debian trixie](https://www.xiboplayer.org/docs/players/arexibo) apt repo
- Minimal X11 (`xinit` + openbox) for Qt rendering
- `first-boot-kiosk.service` reads `/boot/firmware/kiosk.conf`, sets hostname, writes
  `/etc/mmek/arexibo.env`, enables display + player units, strips `CMS_KEY` from bootfs
- HDMI forced toward **1920×1080** (Glance & Match canvas)
- SSH enabled at build time with **pubkey-only** when a deploy key is provided to CI

CMS credentials are **never** baked into the golden image.

## Per-kiosk config

### GitHub Actions (preferred)

Actions → **Kiosk config** → Run workflow:

- `location` (e.g. `lobby`)
- `unit` (e.g. `01`) → hostname `kiosk-lobby-01`
- `cms_url`, `cms_key`
- optional `display_group`, `image_version`

Download the `*-config.zip` artifact (contains secrets — do not attach to Releases).

### Local

```bash
python3 ops/players/image/generate_kiosk_config.py \
  --location lobby --unit 01 \
  --cms-url https://cms.example.local \
  --cms-key "$CMS_KEY" \
  --image-version "$(cat ops/players/image/VERSION)" \
  --out-dir /tmp/kiosk-configs
```

Copy `kiosk.conf` to the SD card boot partition as `/boot/firmware/kiosk.conf`
before first power-on.

## Flash an approved image

1. Download `.img.xz` + `sha256sums.txt` from the GitHub Release `player-image-v*`
   (or a soak artifact from a dispatch build).
2. Verify checksum; flash to SD.
3. Place generated `kiosk.conf` on the boot partition.
4. DHCP reservation for the Pi MAC; power on; authorize display in CMS into the
   location display group.

## Build notes (CI)

- Runner: `ubuntu-24.04-arm` (native arm64). Private orgs need ARM runner entitlement.
- Action: [`usimd/pi-gen-action`](https://github.com/usimd/pi-gen-action) with
  `pi-gen-version: arm64`, stages `stage0 stage1 stage2` + this `stage-kiosk`.
- Optional repo secret `KIOSK_SSH_PUBKEY` injects `authorized_keys` for the first user.
- Optional `AREXIBO_VERSION` workflow input pins the apt package; otherwise latest
  from the xiboplayer repo is installed and recorded under `/etc/mmek/arexibo-package-version`.

If the arm64 Arexibo package is unavailable for the Pi OS release, the stage **fails**
(no silent unsigned binary fallback).

## Local pi-gen (optional)

Requires a Debian/Ubuntu host (or Docker) with pi-gen `arm64` branch. Prefer CI.
See the Player image workflow for the exact stage list and compression settings.
