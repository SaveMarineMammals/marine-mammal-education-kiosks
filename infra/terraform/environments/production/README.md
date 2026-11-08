# Production DNS (facility)

Composes `dns-facility` + `acme-route53-iam` for Belize kiosks.

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
