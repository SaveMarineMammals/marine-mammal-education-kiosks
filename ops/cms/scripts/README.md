# CMS host scripts

Shell helpers for a dedicated Ubuntu Server mini PC running **Xibo CMS** in Docker.

| Script | Purpose |
| --- | --- |
| [`bootstrap-cms-host.sh`](bootstrap-cms-host.sh) | apt upgrade, Docker + Compose, UFW (22/80/9505), unattended-upgrades |
| [`install-xibo-cms.sh`](install-xibo-cms.sh) | Download official Xibo Docker bundle into `/opt/xibo` and `docker compose up -d` |

Full procedure: [`../../runbooks/install-cms-host.md`](../../runbooks/install-cms-host.md).

Run on the CMS host after Ubuntu is installed:

```bash
chmod +x *.sh
sudo ./bootstrap-cms-host.sh
# re-login for docker group
sudo ./install-xibo-cms.sh
```
