variable "aws_region" {
  description = "AWS region for the Terraform state bucket and lock table"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project prefix used in resource names"
  type        = string
  default     = "mmek"
}

variable "github_repository" {
  description = "GitHub repository slug (owner/name) used in docs and legacy OIDC sub claims"
  type        = string
}

variable "github_org_id" {
  description = "Numeric GitHub organization/user node id for immutable OIDC sub (gh api orgs/ORG --jq .id)"
  type        = string
}

variable "github_repository_id" {
  description = "Numeric GitHub repository node id for immutable OIDC sub (gh api repos/ORG/REPO --jq .id)"
  type        = string
}

variable "state_bucket_name" {
  description = "Optional fixed S3 bucket name; defaults to {project}-terraform-state-{account_id}"
  type        = string
  default     = ""
}

variable "github_oidc_provider_arn" {
  description = "Existing GitHub Actions OIDC provider ARN (reuse if mmap bootstrap already created one). Empty creates a new provider."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags applied to bootstrap resources"
  type        = map(string)
  default     = {}
}
