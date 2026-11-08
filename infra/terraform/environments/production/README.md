# Production DNS (facility)

Composes `dns-facility` + `acme-route53-iam` for Belize kiosks, and optionally
`admin-alert` when Sent/SES secrets are provided as `TF_VAR_*` / GitHub
Environment secrets (see
[`ops/runbooks/sent-dm-alerts.md`](../../../../ops/runbooks/sent-dm-alerts.md)).
Without those secrets, apply correctly reports **0 added** for the Lambda.

## Prerequisites

1. [`../../bootstrap`](../../bootstrap/) applied; GitHub secrets set.
2. Parent hosted zone `savemarinemammals.com` already in this AWS account.

## Apply (CI)

With `TF_INFRA_ENABLED=true`, pushes to `main` that touch `infra/**` run
[`infra-cd.yml`](../../../../.github/workflows/infra-cd.yml).

## Apply (local)

```powershell
cd infra/terraform/environments/production
# After bootstrap outputs:
..\..\..\scripts\terraform-init.ps1 `
  -Bucket mmek-terraform-state-ACCOUNT `
  -Key production/terraform.tfstate `
  -Region us-east-1 `
  -LockTable mmek-terraform-locks
..\..\..\scripts\terraform-plan.ps1
..\..\..\scripts\terraform-apply.ps1
```

Or bash equivalents under [`../../../scripts/`](../../../scripts/).

## After apply — CMS TLS

```powershell
terraform output -raw kiosks_zone_id
terraform output -raw acme_access_key_id
terraform output -raw acme_secret_access_key
```

Write `/etc/mmek/caddy-acme.env` on the CMS host (see
[`../../../../ops/cms/caddy/`](../../../../ops/cms/caddy/)), then
`sudo ./enable-cms-tls.sh`.

## After apply — admin alerts (optional)

1. Add `MMEK_*` secrets on the `production` GitHub Environment (list in
   [`sent-dm-alerts.md`](../../../../ops/runbooks/sent-dm-alerts.md)).
2. Re-run Infra apply; confirm plan adds the Lambda (not 0 resources).
3. Read the URL:

```powershell
terraform output -raw alert_lambda_url
```

4. Put the URL and ingest token in CMS `/etc/mmek/alert.env` and optional player
   `kiosk.conf` `ALERT_*` keys
   ([`security-patching.md`](../../../../ops/runbooks/security-patching.md)).
