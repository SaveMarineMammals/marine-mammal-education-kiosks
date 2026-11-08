# Runbook: automated security patching

Keep the facility **CMS** and **kiosk players** patched with automation during
**01:00–05:00 device local time** (timezone default `America/Belize`). Permanent
failures notify admins by **SMS (Sent.dm)** and **email (SES)** via an AWS Lambda.

Sent account/template setup: [`sent-dm-alerts.md`](sent-dm-alerts.md).

## What is automated

| Host | Mechanism | Disruptive window |
| --- | --- | --- |
| CMS Ubuntu | `unattended-upgrades` + reboot ~02:00; `mmek-cms-stack-update.timer` ~02:15 (`docker compose pull` + smoke) | 01:00–05:00 local |
| Players (golden image **1.0.5+**) | `unattended-upgrades` + reboot ~02:00; `mmek-post-update-health` after boot | 01:00–05:00 local |

Arexibo stays **`apt-mark hold`**. Player app / base-stack bumps still require a new
golden image + reflash ([`replace-pi.md`](replace-pi.md)).

## Alert path

```text
Host permanent failure
  → /usr/local/sbin/mmek-admin-alert
  → POST Function URL (Bearer token)
  → Lambda: SES email + Sent.dm SMS
```

Host env (`/etc/mmek/alert.env`): **only** `ALERT_LAMBDA_URL` and
`ALERT_INGEST_TOKEN` (+ optional `ALERT_ROLE` / `ALERT_HOSTNAME`). Dedup markers
live under `/var/lib/mmek/alert-sent/<code>`.

Clear a dedup / failure counter after fixing:

```bash
sudo rm -f /var/lib/mmek/alert-sent/<code>
sudo rm -f /var/lib/mmek/cms-stack-update-failures   # CMS
sudo rm -f /var/lib/mmek/post-update-health-failures # player
```

## CMS install

After Xibo/TLS/Tailscale ([`install-cms-host.md`](install-cms-host.md)):

```bash
cd /path/to/marine-mammal-education-kiosks/ops/cms
sudo ./scripts/install-security-updates.sh
sudo nano /etc/mmek/alert.env   # from terraform output alert_lambda_url
```

Forced stack update (ignores hour window):

```bash
sudo MMEK_FORCE_UPDATE=1 /usr/local/sbin/cms-stack-update
```

## Players

1. Flash recipe **1.0.5+** (`player-image-v*`).
2. Generate `kiosk.conf` with optional alert flags:

```bash
python3 ops/players/image/generate_kiosk_config.py \
  --location lobby --unit 01 \
  --cms-url https://server.kiosks.local.belize.savemarinemammals.com \
  --cms-key "$CMS_KEY" \
  --ts-authkey "$TS_AUTHKEY" \
  --alert-lambda-url "$ALERT_LAMBDA_URL" \
  --alert-ingest-token "$ALERT_INGEST_TOKEN" \
  --image-version 1.0.5 \
  --out-dir /tmp/kiosk-configs
```

## Still manual (expect an alert)

- Xibo **major** CMS upgrades / schema migrations
- Custom **xcaddy** rebuild after Caddy CVE
- New Arexibo pin / golden image rollout
- Hardware or SD failure
- SES/Sent misconfiguration (Lambda returns 502)

## Related

- [`sent-dm-alerts.md`](sent-dm-alerts.md) — Sent.dm + Terraform secrets
- [`infra/terraform/modules/admin-alert/`](../../infra/terraform/modules/admin-alert/)
- [`install-cms-host.md`](install-cms-host.md), [`ops/players/README.md`](../players/README.md)
