# CMS host scripts

Shell helpers for a dedicated Ubuntu Server mini PC running **Xibo CMS** in Docker.

| Script | Purpose |
| --- | --- |
| [`bootstrap-cms-host.sh`](bootstrap-cms-host.sh) | apt upgrade, Docker + Compose, UFW (22/80/443/9505), unattended-upgrades |
| [`install-xibo-cms.sh`](install-xibo-cms.sh) | Download official Xibo Docker bundle into `/opt/xibo` and `docker compose up -d` |
| [`enable-cms-tls.sh`](enable-cms-tls.sh) | Caddy + Let's Encrypt **DNS-01** (Route 53) for `server.kiosks.local.belize.savemarinemammals.com`; bind `cms-web` to `127.0.0.1:8080` |
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
# after OAuth app exists in Xibo UI:
sudo ./deploy-cms-sync.sh \
  --repo-url git@github.com:ORG/marine-mammal-education-kiosks.git \
  --runner-token <TOKEN> \
  --cms-url http://127.0.0.1:8080
```
