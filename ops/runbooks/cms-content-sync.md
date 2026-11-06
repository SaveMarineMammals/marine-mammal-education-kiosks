# Runbook: CMS content sync (Git main → Xibo)

Keep **Library media** and **stable layouts** on the facility Xibo CMS aligned
with Git `main`. **Schedules stay local** — operators decide which exhibits are
active by binding campaigns in the CMS UI.

## What syncs

| Synced | Not synced |
| --- | --- |
| Media for `status: published` exhibits | Draft / review / retired content |
| Layout named `mmek-<slug>` (update in place) | Schedules, display groups, XMR actions |

Stable layout names preserve `campaignId` so existing schedules keep working
when content refreshes.

## One-time host setup

Prerequisites: Xibo CMS already running ([install-cms-host.md](install-cms-host.md)).

1. In CMS → **Applications**, create a **Client Credentials** application.
   Record client id/secret (least privilege; Library + Layout scopes as available).
2. Create a GitHub Actions **runner registration token** for this repo
   (Settings → Actions → Runners → New self-hosted runner).
3. On the CMS host, from a checkout of this repo (or after cloning once):

   ```bash
   sudo ./ops/cms/scripts/deploy-cms-sync.sh \
     --repo-url git@github.com:ORG/marine-mammal-education-kiosks.git \
     --runner-token <REGISTRATION_TOKEN> \
     --cms-url http://127.0.0.1
   ```

4. Edit `/etc/mmek/cms-sync.env` (not a copy under `/opt/mmek/`) with
   `XIBO_CLIENT_ID` / `XIBO_CLIENT_SECRET` (and `MEDIA_STORE_URI` if large
   masters live on a NAS/S3 mount). The deploy script keeps this file
   `root:mmek-runner` mode `640`.
5. Re-run deploy to enable the timer and smoke OAuth:

   ```bash
   sudo /opt/mmek/repo/ops/cms/scripts/deploy-cms-sync.sh --skip-runner
   ```

6. Optional first live sync:

   ```bash
   sudo /opt/mmek/repo/ops/cms/scripts/deploy-cms-sync.sh --skip-runner --live-sync
   ```

The deploy script installs:

- Repo at `/opt/mmek/repo` (tracks `main` + Git LFS)
- Python venv at `/opt/mmek/venv`
- Env file `/etc/mmek/cms-sync.env`
- systemd `mmek-cms-sync.timer` (daily ~05:30 local safety net)
- Self-hosted Actions runner labeled `mmek-cms`, running as system user `mmek-runner`
  (`config.sh` refuses to register when the installer is root)

## Ongoing triggers

| Trigger | Mechanism |
| --- | --- |
| Merge to `main` (exhibits/framework/tools) | Workflow [`.github/workflows/cms-sync.yml`](../../.github/workflows/cms-sync.yml) on the self-hosted runner |
| Daily | Same workflow cron **and** `mmek-cms-sync.timer` |
| Manual | Actions → **CMS content sync** → Run workflow, or `sudo systemctl start mmek-cms-sync.service` |

Both paths call `tools/sync_cms.py --all-published` (with flock so they cannot overlap).

## After an exhibit is published

1. Set `exhibit.yaml` `status: published`, merge to `main`.
2. Wait for **CMS content sync** (or start the systemd unit).
3. In CMS, schedule campaign **`mmek-<slug>`** onto the intended display groups
   (see exhibit `schedule/intent.yaml` for human intent only).
4. Spot-check a physical player.

## Operator commands

```bash
# Dry-run on the host
sudo -E bash -c 'set -a; source /etc/mmek/cms-sync.env; set +a; \
  /opt/mmek/venv/bin/python /opt/mmek/repo/tools/sync_cms.py --all-published --dry-run'

# Live reconcile (also pulls main when using the wrapper)
sudo /opt/mmek/repo/ops/cms/scripts/run-cms-sync.sh

# Timer status
systemctl status mmek-cms-sync.timer
journalctl -u mmek-cms-sync.service -n 100 --no-pager
```

## Boundary reminder

`tools/xibo_client.py` deliberately has **no schedule APIs**. Do not extend
production sync to edit schedules without an explicit ops decision.
