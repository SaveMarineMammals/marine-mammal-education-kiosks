# Runbook: install Xibo CMS host (Beelink / mini PC)

Stand up a dedicated **Ubuntu Server + Docker** host for **Xibo CMS Open Source
Edition**. This is the facility CMS; kiosk Pis are separate (see
[`../players/`](../players/)).

Companion scripts live in [`../cms/scripts/`](../cms/scripts/). Copy them from
this repo (clone/USB share) onto the CMS host after Ubuntu is installed.

## Hardware assumptions

- x86-64 mini PC (e.g. Beelink Mini S), **≥ 8 GB RAM** (12 GB fine), **≥ 128 GB**
  SSD, wired Ethernet preferred.
- Bootable USB written from the official Ubuntu Server 24.04 LTS live ISO with
  **Rufus**, **balenaEtcher**, or an equivalent raw ISO writer (not Ventoy).

## 0. Prepare the installer USB (Windows workstation)

1. Download **Ubuntu Server 24.04 LTS** (`ubuntu-24.04*-live-server-amd64.iso`) from
   <https://ubuntu.com/download/server> and verify the published SHA256.
2. Flash the ISO **directly** to the USB stick:

   | Tool | Notes |
   | --- | --- |
   | [balenaEtcher](https://etcher.balena.io/) | Select ISO → select USB → Flash |
   | [Rufus](https://rufus.ie/) | Partition scheme **GPT**, target **UEFI**. If the stick is a USB SSD/HDD enclosure (e.g. ADATA), enable **List USB Hard Drives** (`rufus.exe -x`) so the drive appears. Prefer **DD Image** mode when Rufus offers ISO vs DD for this hybrid ISO. |

3. Confirm the Beelink boot menu lists the USB as a UEFI removable/USB device.

Post-install helpers are **not** stored on the flashed ISO volume (raw write
replaces the whole stick). Use this Git repo’s `ops/cms/scripts/` after first boot.

## 1. Firmware

1. Plug Ethernet into the facility LAN.
2. Plug in the Ubuntu installer USB.
3. Power on → open Boot Menu (Beelink often **F7** / **F12** / **Esc**).
4. Boot the USB in **UEFI** mode (not legacy CSM).
5. Proceed with the Ubuntu Server live installer.

Optional BIOS checks: disable Secure Boot only if Ubuntu fails to boot; prefer
leaving it on when possible. Disable Fast Boot if USB is skipped.

## 2. Ubuntu Server install (Subiquity)

Use these choices unless facility policy differs:

| Prompt | Choice |
| --- | --- |
| Language / keyboard | Facility locale |
| Network | DHCP on Ethernet (note MAC for a reservation later) |
| Proxy | None unless required |
| Mirror | Default |
| Guided storage | Use entire local SSD (wipe Windows) |
| Profile | Local admin user + hostname e.g. `cms-facility-01` |
| SSH | **Install OpenSSH server** |
| Featured snaps | Skip |

Finish → reboot → remove USB when prompted.

## 3. First login on the LAN

From an admin workstation:

```bash
ssh <admin>@<cms-ip-or-hostname>
sudo apt update && sudo apt upgrade -y
sudo reboot
```

Reserve the CMS MAC in DHCP; optional DNS name `cms.<site>.local` (see
[`../networking/README.md`](../networking/README.md)).

## 4. Copy setup scripts from this repo

On the CMS host (git clone, `scp`, or any other copy of the monorepo):

```bash
cd /path/to/marine-mammal-education-kiosks/ops/cms
chmod +x scripts/*.sh
```

## 5. Bootstrap host + install Xibo

```bash
sudo ./scripts/bootstrap-cms-host.sh
# log out/in (or newgrp docker) so docker works without sudo
sudo ./scripts/install-xibo-cms.sh
```

`bootstrap-cms-host.sh` installs Docker Compose v2, UFW (SSH/80/9505), and
unattended security updates. `install-xibo-cms.sh` deploys official Xibo Docker
files under `/opt/xibo` (requires sudo).

Default CMS UI: `http://<cms-ip>/` — login `xibo_admin` / `password`, then
**change the password immediately**.

## 6. CMS project conventions

1. Library folders: `exhibits/`, `framework/branding/`, `framework/playlists/`
   ([`../cms/README.md`](../cms/README.md)).
2. Display groups by location (`lobby`, …), not by exhibit.
3. Record **CMS Key** for Pi `kiosk.conf`.
4. Create an API application; put URL + secrets in a **local** `.env` from the
   repo `.env.example` — never commit secrets.
5. Schedule a smoke-test layout to one display group; enroll a Pi per
   [`../players/README.md`](../players/README.md).

## 7. Backup

- Nightly copy of `/opt/xibo/shared/` (database + library) to NAS or external disk.
- Keep `config.env` MySQL password with other facility secrets (not in Git).

## 8. HTTPS (optional)

On a private locked LAN, HTTP is acceptable for day one. For broader exposure,
terminate TLS with nginx/Caddy in front of `cms-web` (Xibo Docker does not ship
SSL). See [Xibo for Docker](https://account.xibosignage.com/docs/setup/xibo-for-docker).

## References

- [`../cms/README.md`](../cms/README.md) — folders, tags, credentials
- [`../../docs/local-testing.md`](../../docs/local-testing.md) — production CMS smoke steps
- [`../../docs/architecture.md`](../../docs/architecture.md) — content flow
- Official install: <https://account.xibosignage.com/docs/setup/xibo-for-docker>
