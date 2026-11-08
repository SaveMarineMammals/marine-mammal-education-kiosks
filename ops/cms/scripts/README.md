# CMS host scripts

Shell helpers for a dedicated Ubuntu Server mini PC running **Xibo CMS** in Docker.

| Script | Purpose |
| --- | --- |
| [`bootstrap-cms-host.sh`](bootstrap-cms-host.sh) | apt upgrade, Docker + Compose, UFW (22/80/443/9505), unattended-upgrades |
| [`install-xibo-cms.sh`](install-xibo-cms.sh) | Download official Xibo Docker bundle into `/opt/xibo` and `docker compose up -d` |
| [`enable-cms-tls.sh`](enable-cms-tls.sh) | Caddy + Let's Encrypt **DNS-01** (Route 53) for `server.kiosks.local.belize.savemarinemammals.com`; bind `cms-web` to `127.0.0.1:8080` |
| [`install-tailscale.sh`](install-tailscale.sh) | Join Tailscale as `tag:mmek-cms`; tighten UFW to `tailscale0` + facility LAN CIDR |
| [`install-cms-split-dns.sh`](install-cms-split-dns.sh) | dnsmasq on `tailscale0` answering the CMS hostname with this host's `100.x` (Tailscale split DNS) |
| [`install-security-updates.sh`](install-security-updates.sh) | Off-hours unattended reboot, stack-update timer, admin-alert helper |
| [`cms-stack-update.sh`](cms-stack-update.sh) | `docker compose pull` + smoke (invoked by timer) |
| [`mmek-admin-alert.sh`](mmek-admin-alert.sh) | POST permanent failures to the admin-alert Lambda |
| [`deploy-cms-sync.sh`](deploy-cms-sync.sh) | Idempotent content-sync install (repo, venv, env, timer, Actions runner) |
| [`run-cms-sync.sh`](run-cms-sync.sh) | Pull `main` + run `tools/sync_cms.py --all-published` (systemd entrypoint) |

Caddy / ACME: [`../caddy/README.md`](../caddy/README.md) (Route 53 DNS-01).

Full CMS install: [`../../runbooks/install-cms-host.md`](../../runbooks/install-cms-host.md).

Content sync: [`../../runbooks/cms-content-sync.md`](../../runbooks/cms-content-sync.md).

```bash
chmod +x *.sh
sudo ./bootstrap-cms-host.sh
# re-login for docker group
sudo ./install-xibo-cms.sh
# after /etc/mmek/caddy-acme.env has Route 53 IAM keys:
sudo ./enable-cms-tls.sh
# facility Tailscale (players + operators); see ../../runbooks/facility-tailscale.md
sudo FACILITY_LAN_CIDR=192.168.1.0/24 TS_AUTHKEY=tskey-auth-… ./install-tailscale.sh
sudo ./install-cms-split-dns.sh
# then Tailscale admin → split DNS for kiosks.local.belize.savemarinemammals.com
sudo ./install-security-updates.sh
# fill /etc/mmek/alert.env (ops/runbooks/sent-dm-alerts.md)
# after OAuth app exists in Xibo UI:
sudo ./deploy-cms-sync.sh \
  --repo-url git@github.com:ORG/marine-mammal-education-kiosks.git \
  --runner-token <TOKEN> \
  --cms-url http://127.0.0.1:8080
```
