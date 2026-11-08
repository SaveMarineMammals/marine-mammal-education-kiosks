# Infra pipelines (AWS / Terraform)

Facility DNS and Let's Encrypt ACME IAM for education kiosks live under
[`infra/`](../infra/). CI mirrors the assessment repo pattern (OIDC + remote
state) with bash helpers instead of Node.

## Bootstrap (once per AWS account)

```powershell
cd infra/bootstrap
copy terraform.tfvars.example terraform.tfvars
# set github_repository; reuse github_oidc_provider_arn if mmap already created OIDC
terraform init
terraform apply
terraform output github_actions_secrets
```

Add repository secrets: `AWS_TERRAFORM_ROLE_ARN`, `TF_STATE_BUCKET`,
`TF_LOCK_TABLE`. Set variable `TF_INFRA_ENABLED=true`. Create GitHub Environment
`production` for apply approval if desired.

## Zones

| Zone | Managed by |
| --- | --- |
| `savemarinemammals.com` | Existing (mmap / registrar) — **not** recreated here |
| `belize.savemarinemammals.com` | `dns-facility` module + NS in parent |
| `kiosks.local.belize.savemarinemammals.com` | `dns-facility` module + NS in belize; **LE DNS-01** |

CMS hostname: `server.kiosks.local.belize.savemarinemammals.com` (A record from
`cms_server_ipv4` in production tfvars).

## Workflows

| Workflow | When |
| --- | --- |
| [Infra plan](../.github/workflows/infra-ci.yml) | PRs touching `infra/**` |
| [Infra apply](../.github/workflows/infra-cd.yml) | Push to `main` touching `infra/**`, or `workflow_dispatch` |

When `TF_INFRA_ENABLED` is not `true`, jobs skip as pass so branch protection is
not blocked before bootstrap.

## After apply → CMS TLS

```text
terraform output -raw kiosks_zone_id
terraform output -raw acme_access_key_id
terraform output -raw acme_secret_access_key
```

Populate `/etc/mmek/caddy-acme.env` on the CMS host and run
[`ops/cms/scripts/enable-cms-tls.sh`](../ops/cms/scripts/enable-cms-tls.sh).
Details: [`ops/cms/caddy/README.md`](../ops/cms/caddy/README.md).
