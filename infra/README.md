# Infrastructure (AWS / Terraform)

AWS resources for Marine Mammal Education Kiosks: facility DNS, Let's Encrypt
DNS-01 (Route 53), and the optional **admin-alert** Lambda (SES + Sent.dm).
Pattern mirrors
[`marine-mammal-assessment/infra`](https://github.com/SaveMarineMammals/marine-mammal-assessment/tree/main/infra)
with a narrower scope (no VPC/CDN).

| Path | Role |
| --- | --- |
| [`bootstrap/`](bootstrap/) | One-time: S3 state, DynamoDB lock, GitHub OIDC role (local state) |
| [`terraform/modules/dns-facility/`](terraform/modules/dns-facility/) | Nested hosted zones under `savemarinemammals.com` |
| [`terraform/modules/acme-route53-iam/`](terraform/modules/acme-route53-iam/) | IAM user for Caddy ACME on the kiosks zone |
| [`terraform/modules/admin-alert/`](terraform/modules/admin-alert/) | Lambda Function URL: SES email + Sent.dm SMS |
| [`terraform/environments/production/`](terraform/environments/production/) | Composed facility DNS (+ optional admin-alert) stack |
| [`scripts/`](scripts/) | `terraform-init` / `plan` / `apply` helpers for CI |

## DNS layout

```text
savemarinemammals.com                    (existing parent zone — mmap / registrar)
└── belize.savemarinemammals.com         (this stack)
    └── kiosks.local.belize.savemarinemammals.com   (this stack; LE DNS-01 here)
        └── server                       (CMS A/AAAA — optional tfvar)
```

Parent NS for `belize` is written into the existing `savemarinemammals.com` zone.
Child NS for `kiosks.local` is written into the `belize` zone.

## Pipelines

| Workflow | Trigger | Behavior |
| --- | --- | --- |
| [`infra-ci.yml`](../.github/workflows/infra-ci.yml) | PR → `main` (path-filtered) | `terraform plan` when `vars.TF_INFRA_ENABLED=true` |
| [`infra-cd.yml`](../.github/workflows/infra-cd.yml) | Push → `main` (path-filtered) | `terraform apply` to production |

Repo secrets (from bootstrap outputs): `AWS_TERRAFORM_ROLE_ARN`, `TF_STATE_BUCKET`,
`TF_LOCK_TABLE`. Optional variable: `AWS_REGION` (default `us-east-1`).

## Operator quick start

1. Bootstrap once (local AWS admin credentials): see [`bootstrap/README.md`](bootstrap/README.md).
2. Set GitHub secrets from bootstrap `github_actions_secrets` output; set
   `TF_INFRA_ENABLED=true`.
3. Apply production (CI on `main`, or locally with backend config): see
   [`terraform/environments/production/README.md`](terraform/environments/production/README.md).
4. Copy ACME IAM outputs into `/etc/mmek/caddy-acme.env` on the CMS host, then run
   [`ops/cms/scripts/enable-cms-tls.sh`](../ops/cms/scripts/enable-cms-tls.sh).

Docs: [`docs/infra-pipelines.md`](../docs/infra-pipelines.md).
