# CMS host scripts

Shell helpers for a dedicated Ubuntu Server mini PC running **Xibo CMS** in Docker.

| Script | Purpose |
| --- | --- |
| [`bootstrap-cms-host.sh`](bootstrap-cms-host.sh) | apt upgrade, Docker + Compose, UFW (22/80/9505), unattended-upgrades |
| [`install-xibo-cms.sh`](install-xibo-cms.sh) | Download official Xibo Docker bundle into `/opt/xibo` and `docker compose up -d` |
| [`deploy-cms-sync.sh`](deploy-cms-sync.sh) | Idempotent content-sync install (repo, venv, env, timer, Actions runner) |
| [`run-cms-sync.sh`](run-cms-sync.sh) | Pull `main` + run `tools/sync_cms.py --all-published` (systemd entrypoint) |

Full CMS install: [`../../runbooks/install-cms-host.md`](../../runbooks/install-cms-host.md).

Content sync: [`../../runbooks/cms-content-sync.md`](../../runbooks/cms-content-sync.md).

```bash
chmod +x *.sh
sudo ./bootstrap-cms-host.sh
# re-login for docker group
sudo ./install-xibo-cms.sh
# after OAuth app exists in Xibo UI:
sudo ./deploy-cms-sync.sh \
  --repo-url git@github.com:ORG/marine-mammal-education-kiosks.git \
  --runner-token <TOKEN> \
  --cms-url http://127.0.0.1
```
