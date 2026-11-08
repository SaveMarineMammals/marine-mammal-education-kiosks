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

**Never** put `CMS_KEY` (or generated `kiosk.conf` / `*-config.zip`) into GitHub
Actions inputs, workflow artifacts, Issues, or PRs. Generate config **only on a
trusted local machine**.

## Image / config as code

### 1. Build or pick an approved golden image

- **Approved fleet image:** GitHub Release tagged `player-image-v*` (e.g.
  `player-image-v1.0.0`). Built by [`.github/workflows/player-image.yml`](../../.github/workflows/player-image.yml).
- **Soak / pre-release:** Actions → **Player image** → Run workflow
  (`workflow_dispatch`). Download the run artifact (retained ~30 days); do not
  flash soak builds to production until approved and released.

Recipe details: [`image/`](image/).

### 2. Download the image locally

Requires [GitHub CLI](https://cli.github.com/) (`gh auth login`). Run these from
a clone of this repo so `gh` picks up the remotes (Linux/WSL):

**From an approved Release (preferred for production):**

```bash
mkdir -p ~/Downloads/mmek-images
# List releases if needed:
gh release list | grep player-image

TAG=player-image-v1.0.0   # match the approved tag
gh release download "$TAG" \
  --pattern 'mmek-kiosk-*' \
  --pattern 'sha256sums.txt' \
  --pattern 'build-info.txt' \
  --dir ~/Downloads/mmek-images
ls -lh ~/Downloads/mmek-images
```

**From a workflow_dispatch soak build:**

Each dispatch run gets a unique version `{VERSION}-b.{run_number}` (e.g.
`1.0.0-b.42`). Artifact name is `mmek-kiosk-<that-version>`.

```bash
mkdir -p ~/Downloads/mmek-images
gh run list --workflow=player-image.yml --limit 5

RUN_ID=123456789          # successful run id from the list
# List artifact names for that run (includes the generated version):
gh run view "$RUN_ID" --json artifacts --jq '.artifacts[].name'

VERSION=1.0.0-b.42        # from artifact name / build-info.txt
gh run download "$RUN_ID" \
  --name "mmek-kiosk-${VERSION}" \
  --dir ~/Downloads/mmek-images
ls -lh ~/Downloads/mmek-images
grep recipe_version ~/Downloads/mmek-images/build-info.txt
```

**Verify checksum:**

```bash
cd ~/Downloads/mmek-images
sha256sum -c sha256sums.txt
```

### 3. Generate per-kiosk config (local only)

```bash
cd /path/to/marine-mammal-education-kiosks
export CMS_KEY='…'   # from CMS; do not commit or paste into Actions
python3 ops/players/image/generate_kiosk_config.py \
  --location lobby --unit 01 \
  --cms-url https://cms.example.local \
  --cms-key "$CMS_KEY" \
  --image-version "$(grep '^recipe_version=' ~/Downloads/mmek-images/build-info.txt | cut -d= -f2)" \
  --out-dir /tmp/kiosk-configs
# writes /tmp/kiosk-configs/kiosk-lobby-01/kiosk.conf (+ zip); keep private
# --image-version should match the flashed image (Release tag or soak build-info).
```

Full flags: [`image/README.md`](image/README.md).

### 4. Flash the SD card

Identify the SD device carefully (`lsblk`). **Wrong `of=` destroys disks.**

```bash
# Example device — confirm yours (often /dev/sdX or /dev/mmcblkN)
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL

IMG=~/Downloads/mmek-images/mmek-kiosk-1.0.0-b.42.img.xz   # match downloaded name
DEV=/dev/sdX                                         # NO partition suffix

# Unmount any auto-mounted partitions on that device first
sudo umount "${DEV}"* 2>/dev/null || true

# Write image (xz-compressed) and sync
xzcat "$IMG" | sudo dd of="$DEV" bs=4M status=progress conv=fsync
sudo sync
```

Alternatively use [Raspberry Pi Imager](https://www.raspberrypi.com/software/):
**Choose OS → Use custom** → select the `.img.xz` → select the SD card → Write.
Do **not** apply Imager’s “OS customisation” overlay; first-boot identity comes
from `kiosk.conf` below.

### 5. Place `kiosk.conf` on the boot partition

There is **no** `/bootfs` folder inside the card. After a flash, the SD card’s
**FAT boot volume** is the boot partition (often labeled `bootfs`). Its **root**
holds `config.txt`, `cmdline.txt`, and the kernels. Put `kiosk.conf` **next to
`config.txt`** at that root. On a running Pi that same file is
`/boot/firmware/kiosk.conf`.

**How to recognize it:** you should see `config.txt` and `cmdline.txt` in the
volume root. The large `ext4` rootfs partition is invisible on Windows (that is
normal).

**Windows (Explorer):** open the removable drive letter for the card → copy
`kiosk.conf` into that drive’s root (same folder as `config.txt`) → Eject.

**Windows + WSL** (card appears as e.g. `D:`):

```bash
# Mount the Windows drive letter that shows config.txt
sudo mkdir -p /mnt/d
sudo mount -t drvfs D: /mnt/d
ls /mnt/d/config.txt          # must exist — confirms this is the boot volume
cp /tmp/kiosk-configs/kiosk-demo-01/kiosk.conf /mnt/d/kiosk.conf
sync
sudo umount /mnt/d
# Then Eject the card in Windows before unplugging
```

**Linux desktop** (auto-mount by label):

```bash
BOOT=/media/$USER/bootfs      # or /run/media/$USER/bootfs — ls for config.txt
test -f "$BOOT/config.txt"
cp /tmp/kiosk-configs/kiosk-lobby-01/kiosk.conf "$BOOT/kiosk.conf"
sync
udisksctl unmount -b /dev/sdX1    # boot partition; adjust device
udisksctl power-off -b /dev/sdX
```

### 6. Network, power on, authorize

1. Create a DHCP reservation for the Pi MAC → hostname `kiosk-<location>-<nn>`.
2. Insert the SD card, power on the kiosk; first-boot applies hostname and Arexibo env.
3. In CMS: authorize the display; assign a location/role **display group** (`lobby`,
   not exhibit names).
4. Set display profile to **1920×1080** landscape.

## Bootstrap outline (golden image)

1. Download + verify approved `mmek-kiosk-*` image; flash SD; place `kiosk.conf`
   **before** first power-on (next to `config.txt` on the FAT boot volume).
2. First boot sets hostname `kiosk-<location>-<nn>`, writes Arexibo env, and starts
   `mmek-kiosk-display` + `arexibo` (requires recipe **1.0.1+** for reliable X11/KMS).
3. Authorize the display in CMS; assign to a **display group** by location/role.
4. Set display profile (resolution **1920×1080**, landscape, stats).
5. Verify a known test layout plays offline after CMS cache (see runbook `offline-cache.md`).
6. Confirm USB touch HID is visible if the panel touch cable is connected.
7. Optional SSH smoke test from a workstation with the repo cloned:

   ```bash
   bash ops/scripts/bootstrap-check.sh kiosk-lobby-01
   ```

## Checklist (new Pi)

- [ ] Approved Release (or approved soak) image downloaded and `sha256sum -c` OK
- [ ] SD flashed; `kiosk.conf` on boot partition as `kiosk.conf`
- [ ] Hostname + DHCP reservation set
- [ ] Network + CMS reachable
- [ ] Arexibo registered and authorized as required
- [ ] Display group assigned
- [ ] Test layout plays at 1920×1080
- [ ] Touch HID present (when cabled)
- [ ] Reboot persistence confirmed
- [ ] `bash ops/scripts/bootstrap-check.sh <hostname-or-ip>` passes (optional)
