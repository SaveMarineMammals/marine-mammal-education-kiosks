# Terraform bootstrap (one-time)

Creates remote state storage and the GitHub OIDC role used by CI for
`terraform plan` / `apply`. Uses **local state** in this directory — back up
`terraform.tfstate`; it is not stored in S3.

## Resources

- S3 bucket (versioned, encrypted) for Terraform state
- DynamoDB table for state locking
- GitHub OIDC provider (created only when `github_oidc_provider_arn` is empty)
- IAM role `mmek-terraform-ci` trusted by this repository

## Run locally

Requires AWS credentials that can create S3, DynamoDB, and IAM resources.

```powershell
cd infra/bootstrap
copy terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set github_repository, github_org_id, github_repository_id
# (gh api orgs/ORG --jq .id / gh api repos/ORG/REPO --jq .id); reuse OIDC ARN if present
terraform init
terraform apply
terraform output github_actions_secrets
```

GitHub Actions now issues **immutable** OIDC `sub` claims
(`repo:ORG@ORG_ID/REPO@REPO_ID:…`). The terraform-ci trust policy matches that
form (and the legacy `repo:ORG/REPO:*` form).

Add the output map as GitHub repository secrets (`AWS_TERRAFORM_ROLE_ARN`,
`TF_STATE_BUCKET`, `TF_LOCK_TABLE`) and set repository variable
`TF_INFRA_ENABLED=true`. Then apply
[`../terraform/environments/production`](../terraform/environments/production/).

## Re-apply after CI permission changes

Bootstrap is not applied by GitHub Actions (local state). When the
`mmek-terraform-ci` policy grows (e.g. Lambda / SES for admin-alert), re-run
locally with the same `terraform.tfvars`:

```powershell
cd infra/bootstrap
terraform init
terraform apply
```

Then re-run **Infrastructure Deployment** on `main`.

## Reusing an existing OIDC provider

If `marine-mammal-assessment` bootstrap already created
`token.actions.githubusercontent.com` in this account, set
`github_oidc_provider_arn` to that provider ARN so this stack does not try to
create a second one.
