# Kiosk player golden image

Reproducible **Raspberry Pi OS arm64** image for NovoTouch kiosks: Lite base +
Arexibo + first-boot config from `/boot/firmware/kiosk.conf`.

Recipe **base** version: [`VERSION`](VERSION) (e.g. `1.0.0`). Each CI run
assigns a unique **build** version:

| Trigger | Image version | Artifact / image name |
| --- | --- | --- |
| `workflow_dispatch` | `{VERSION}-b.{run_number}` (e.g. `1.0.0-b.42`) | `mmek-kiosk-1.0.0-b.42` |
| Tag `player-image-v1.2.3` | `1.2.3` | `mmek-kiosk-1.2.3` |

That build version is written into the image as `/etc/mmek/image-recipe-version`
and recorded in `build-info.txt`.

## Pipelines

| Workflow | Purpose |
| --- | --- |
| **Player image** (`.github/workflows/player-image.yml`) | Build `.img.xz` on demand (`workflow_dispatch`) or publish approved Releases on tags `player-image-v*` |

There is **no** GitHub Action for per-kiosk config. `CMS_KEY`, `TS_AUTHKEY`, and
generated `kiosk.conf` stay on operator machines only — see
[`../README.md`](../README.md) and
[`../../runbooks/facility-tailscale.md`](../../runbooks/facility-tailscale.md).

Physical mount / BOM: [`docs/facility-physical-setup.md`](../../../docs/facility-physical-setup.md).  
Player ops (download, flash, config): [`ops/players/README.md`](../README.md).

## Authentication (CMS key — not client certificates)

Xibo players use **XMDS** with a shared **CMS Key** plus a per-display hardware key.
Arexibo is configured with `--host` / `--key` (see `stage-kiosk/files/mmek-arexibo-start`).

**Client certificates cannot replace the CMS key.** OAuth client credentials are for
the CMS REST API only. Use HTTPS to the CMS
(`https://server.kiosks.local.belize.savemarinemammals.com`); public Let's Encrypt
chains are trusted via Pi `ca-certificates`.

## What’s in the image

- Raspberry Pi OS Lite (pi-gen `stage0`–`stage2`) + custom `stage-kiosk`
- **Arexibo** pinned to **romoloman/arexibo 0.6.5-1** (mirrored GitHub Release; see
  `vendor/arexibo.manifest.yaml`). Not the older xiboplayer.org apt package (still
  0.4.1 on Debian trixie).
- Minimal X11 (`xinit` + openbox) for Qt rendering: Xorg as root (VT access), openbox as
  `kiosk`, Pi 5 KMS card selection, `Xwrapper` allowing non-console start
- **Tailscale** via `stage-kiosk/04-tailscale` (pkgs.tailscale.com Debian suite; joins on
  first-boot as `tag:mmek-players` via `TS_AUTHKEY`)
- `first-boot-kiosk.service` waits for D-Bus, reads `/boot/firmware/kiosk.conf` (CRLF-safe),
  sets hostname, joins Tailscale, writes `/etc/mmek/arexibo.env`, enables **and starts**
  display + player units, strips `CMS_KEY` / `TS_AUTHKEY` from bootfs
- HDMI / `xrandr` forced toward **1920×1080** (Glance & Match canvas)
- SSH enabled at build time with **pubkey-only** when a deploy key is provided to CI

CMS and Tailscale credentials are **never** baked into the golden image.

### Arexibo pin and upgrade debt

| Pin | Source | Notes |
| --- | --- | --- |
| **0.6.5-1** (current) | [romoloman/arexibo](https://github.com/romoloman/arexibo) v0.6.5 | Validated on Trixie + system Qt **6.8.2**; XMR / Collect Now OK on soak |
| 0.6.6+ / 0.6.9 | same fork | Declares `libqt6*t64 (>= 6.10.2)`; Trixie has no installable Qt 6.10 stack → runtime symbol failures |
| 0.4.1-1 | xiboplayer.org Debian trixie | Older; hit collect-path panic on soak |

Revisit newer Arexibo only when Debian/RPi OS ships Qt ≥ 6.10, upstream ships a
Qt-6.8-linked arm64 `.deb`, or we deliberately vendor a Qt 6.10 SDK (high cost).
The image install pulls Trixie Qt 6.8 WebEngine + pulseaudio packages first,
then rewrites the 0.6.5 `.deb` Depends (`libqt6gui6t64` / `libqt6widgets6t64` →
non-t64 Trixie names) before `dpkg -i` so apt stays consistent for later stages
(Tailscale, export-image). `apt-mark hold arexibo` keeps the pin from drifting.

## Download and flash

Full Linux commands (Release vs soak artifact, `sha256sum`, `xzcat | dd`, boot
partition `kiosk.conf`): [`ops/players/README.md`](../README.md).

## Per-kiosk config (local only)

Generate on a trusted workstation — never via GitHub Actions inputs/artifacts:

```bash
export CMS_KEY='…'      # do not commit
export TS_AUTHKEY='…'   # tag:mmek-players; do not commit
python3 ops/players/image/generate_kiosk_config.py \
  --location lobby --unit 01 \
  --cms-url https://server.kiosks.local.belize.savemarinemammals.com \
  --cms-key "$CMS_KEY" \
  --ts-authkey "$TS_AUTHKEY" \
  --image-version "$IMAGE_VERSION" \
  --out-dir /tmp/kiosk-configs
```

Set `IMAGE_VERSION` to the flashed image’s `recipe_version` from `build-info.txt`
(or the `player-image-v*` tag suffix for Releases)—not only the in-repo base
`VERSION` file, which is the lineage prefix for soak builds.

Copy `kiosk.conf` to the **root of the FAT boot volume** (next to `config.txt`;
not a nested `bootfs/` folder). On the Pi that is `/boot/firmware/kiosk.conf`.

## Build notes (CI)

- Runner: `ubuntu-24.04-arm` (native arm64). Private orgs need ARM runner entitlement.
- Action: [`usimd/pi-gen-action`](https://github.com/usimd/pi-gen-action) with
  `pi-gen-version: arm64`, stages `stage0 stage1 stage2` + this `stage-kiosk`.
- Optional repo secret `KIOSK_SSH_PUBKEY` injects `authorized_keys` for the first user.
- Optional repo secret `KIOSK_USER_PASSWORD` sets the `mmek` account password (otherwise
  an ephemeral random password is used; prefer SSH pubkey).
- Arexibo is installed from a **mirrored** arm64 `.deb` (GitHub Release tag
  `deps-arexibo-*`, see `vendor/arexibo.manifest.yaml`). Upstream
  `dl.xiboplayer.org` returns Cloudflare **403** to GitHub-hosted runners; the
  mirrored pin is romoloman 0.6.5, not xiboplayer.org’s apt version.
  Optional `AREXIBO_VERSION` input must match the mirrored version or the build fails.

If the arm64 Arexibo package is unavailable for the Pi OS release, the stage **fails**
(no silent unsigned binary fallback).

## Local pi-gen (optional)

Requires a Debian/Ubuntu host (or Docker) with pi-gen `arm64` branch. Prefer CI.
See the Player image workflow for the exact stage list and compression settings.
