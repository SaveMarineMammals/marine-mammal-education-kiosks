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

Reserve the CMS MAC in DHCP. Publish DNS **A** (and optional **AAAA**) for
`server.kiosks.local.belize.savemarinemammals.com` → this host (LAN IP is fine).
Players reach the CMS over **Tailscale** for **TCP 443** and **9505** (LAN remains
break-glass). Join the CMS with [`facility-tailscale.md`](facility-tailscale.md)
after bootstrap. Let's Encrypt uses **DNS-01** via Route 53 (no public port 80
required). See [`../networking/README.md`](../networking/README.md) and
[`../cms/caddy/README.md`](../cms/caddy/README.md).

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
# after Route 53 IAM keys are in /etc/mmek/caddy-acme.env (see §8):
sudo ./scripts/enable-cms-tls.sh
# facility Tailscale (CMS + players over the tailnet) — see facility-tailscale.md:
sudo FACILITY_LAN_CIDR=<lan-cidr> TS_AUTHKEY=<tag:mmek-cms-key> ./scripts/install-tailscale.sh
```

`bootstrap-cms-host.sh` installs Docker Compose v2, UFW (SSH/80/443/9505), and
unattended security updates. `install-xibo-cms.sh` deploys official Xibo Docker
files under `/opt/xibo` (requires sudo). `enable-cms-tls.sh` binds `cms-web` to
loopback `:8080`, installs **Caddy** (with Route 53 DNS plugin) for Let's Encrypt
DNS-01 on `server.kiosks.local.belize.savemarinemammals.com`, and serves HTTPS on
**443**. `install-tailscale.sh` joins the CMS as `tag:mmek-cms` and scopes UFW to
the tailnet plus the facility LAN CIDR — required for production player XMDS/XMR
([`facility-tailscale.md`](facility-tailscale.md)).

Default CMS UI after TLS: `https://server.kiosks.local.belize.savemarinemammals.com/`
— login `xibo_admin` / `password`, then **change the password immediately**.
(Temporary HTTP on the LAN IP is available only until TLS is enabled.)

## 6. CMS project conventions

1. Library folders: `exhibits/`, `framework/branding/`, `framework/playlists/`
   ([`../cms/README.md`](../cms/README.md)).
2. Display groups by location (`lobby`, …), not by exhibit.
3. Record **CMS Key** for Pi `kiosk.conf`.
4. Create an API application; put URL + secrets in a **local** `.env` from the
   repo `.env.example` — never commit secrets.
5. Install content sync (repo pull, systemd timer, self-hosted runner):
   [`cms-content-sync.md`](cms-content-sync.md) /
   [`../cms/scripts/deploy-cms-sync.sh`](../cms/scripts/deploy-cms-sync.sh).
6. Schedule a smoke-test layout to one display group; enroll a Pi per
   [`../players/README.md`](../players/README.md).

## 7. Backup

- Nightly copy of `/opt/xibo/shared/` (database + library) to NAS or external disk.
- Keep `config.env` MySQL password with other facility secrets (not in Git).

## 8. HTTPS (Caddy + Let's Encrypt DNS-01)

Xibo Docker does not terminate TLS. Facility CMS uses host **Caddy** in front of
`cms-web`. Certificates come from Let's Encrypt via **DNS-01** against the Route 53
zone `savemarinemammals.com` (TXT `_acme-challenge…`). The CMS can stay on a
private LAN address; inbound port 80 from the internet is **not** required for ACME.

**Before `enable-cms-tls.sh`:**

1. Apply facility DNS ([`../../infra/`](../../infra/) — zones
   `belize.savemarinemammals.com` and
   `kiosks.local.belize.savemarinemammals.com`; A record for the CMS hostname)
2. Write `/etc/mmek/caddy-acme.env` from Terraform outputs (`kiosks_zone_id`,
   ACME access key) using
   [`../cms/caddy/caddy-acme.env.example`](../cms/caddy/caddy-acme.env.example).
   ACME TXT records are created only in the **kiosks.local** zone.
3. Inbound **TCP 443** and **9505** from players (Tailscale + LAN break-glass;
   see [`facility-tailscale.md`](facility-tailscale.md))

```bash
sudo mkdir -p /etc/mmek
sudo cp ops/cms/caddy/caddy-acme.env.example /etc/mmek/caddy-acme.env
sudo chmod 600 /etc/mmek/caddy-acme.env
sudo nano /etc/mmek/caddy-acme.env
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_HOSTED_ZONE_ID from terraform output

sudo ./scripts/enable-cms-tls.sh
curl -fsSI https://server.kiosks.local.belize.savemarinemammals.com/login
```

Details: [`../cms/caddy/README.md`](../cms/caddy/README.md),
[`../../docs/infra-pipelines.md`](../../docs/infra-pipelines.md).

**After first login**, in the CMS UI:

1. Settings → Network: enable **Force HTTPS**
2. Settings → Displays: set **XMR public address** to
   `tcp://server.kiosks.local.belize.savemarinemammals.com:9505`
3. Leave **XMR WebSocket** empty so players use
   `https://server.kiosks.local.belize.savemarinemammals.com/xmr`

On-host content sync should keep using loopback
`http://127.0.0.1:8080` (see [`cms-sync.env.example`](../cms/cms-sync.env.example)),
not the public HTTPS URL.

Re-run `enable-cms-tls.sh` after a Xibo bundle upgrade if compose again publishes
host `:80`. Official reverse-proxy notes:
[Xibo self-hosted CMS](https://docs.xibosignage.com/setup-docs/cms-installation/self-hosted-cms).

## References

- [`../cms/README.md`](../cms/README.md) — folders, tags, credentials
- [`facility-tailscale.md`](facility-tailscale.md) — Tailscale for CMS + players
- [`cms-content-sync.md`](cms-content-sync.md) — Git main → Library + layouts
- [`../../docs/local-testing.md`](../../docs/local-testing.md) — production CMS smoke steps
- [`../../docs/architecture.md`](../../docs/architecture.md) — content flow
- Official install: <https://account.xibosignage.com/docs/setup/xibo-for-docker>
