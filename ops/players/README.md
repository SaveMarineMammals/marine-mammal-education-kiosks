# Raspberry Pi players

Physical mount, BOM, and NovoTouch panel wiring:
[`docs/facility-physical-setup.md`](../../docs/facility-physical-setup.md).

Golden image + first-boot config:
[`ops/players/image/`](image/).

## Target stack

- **Raspberry Pi 5** (8 GB preferred; 4 GB acceptable for static Glance & Match)
- Aluminium **VESA** case mounted to the display rear / wall-mount brackets (not a
  separate wall plate) — see facility doc BOM
- Fleet OS: **golden image** from [`image/`](image/) (Raspberry Pi OS 64-bit Lite + Arexibo)
- Community **Arexibo** player (aarch64), enrolled against the central CMS
- Display: Vivitek NovoTouch LK7530i (or equivalent) via HDMI at **1920×1080**

Official **Xibo for Linux** requires x86-64 and is **not** supported on Raspberry Pi.
Arexibo is community-supported only. Docker QA continues to use the official Linux
player on x86 ([`ops/qa/`](../qa/)).

## Authentication

Players authenticate to XMDS with the shared **CMS Key** (in `kiosk.conf` /
`/etc/mmek/arexibo.env`) plus a per-display hardware key. **Client certificates
cannot replace the CMS key.** Use HTTPS to the CMS; trust the server CA on the Pi.
OAuth client credentials are for the CMS REST API only, not player registration.

## Image / config as code

1. **Build / approve golden image** — Actions → **Player image** (`workflow_dispatch`),
   or tag `player-image-v*` for a Release. Recipe: [`image/`](image/).
2. **Generate per-kiosk config** — Actions → **Kiosk config** (inputs: location, unit,
   cms_url, cms_key, …) or run [`image/generate_kiosk_config.py`](image/generate_kiosk_config.py)
   locally. Download the `*-config.zip` artifact (contains secrets — do not commit).
3. **Flash** the approved `.img.xz`, copy `kiosk.conf` to `/boot/firmware/kiosk.conf`,
   set DHCP reservation, power on.
4. **Authorize** the display in CMS; assign a location/role **display group**.

## Bootstrap outline (golden image)

1. Flash approved `mmek-kiosk-*` image; place generated `kiosk.conf` on the boot partition.
2. First boot sets hostname `kiosk-<location>-<nn>` and Arexibo env from the conf.
3. Authorize the display in CMS; assign to a **display group** by location/role (`lobby`, not exhibit names).
4. Set display profile (resolution **1920×1080**, landscape, stats).
5. Verify a known test layout plays offline after CMS cache (see runbook `offline-cache.md`).
6. Confirm USB touch HID is visible if the panel touch cable is connected.
7. Optional: `ops/scripts/bootstrap-check.sh <hostname-or-ip>`.

## Checklist (new Pi)

- [ ] Approved golden image flashed
- [ ] Generated `kiosk.conf` on `/boot/firmware/`
- [ ] Hostname + DHCP reservation set
- [ ] Network + CMS reachable
- [ ] Arexibo registered and authorized as required
- [ ] Display group assigned
- [ ] Test layout plays at 1920×1080
- [ ] Touch HID present (when cabled)
- [ ] Reboot persistence confirmed
