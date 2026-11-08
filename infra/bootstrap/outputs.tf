output "terraform_state_bucket" {
  description = "S3 bucket for Terraform remote state"
  value       = aws_s3_bucket.terraform_state.bucket
}

output "terraform_lock_table" {
  description = "DynamoDB table for Terraform state locking"
  value       = aws_dynamodb_table.terraform_lock.name
}

output "terraform_ci_role_arn" {
  description = "IAM role ARN for GitHub Actions Terraform plan/apply (OIDC)"
  value       = aws_iam_role.terraform_ci.arn
}

output "github_oidc_provider_arn" {
  description = "GitHub Actions OIDC provider ARN used by the terraform-ci role"
  value       = local.github_oidc_provider_arn
}

output "github_actions_secrets" {
  description = "Add these as GitHub repository secrets or variables"
  value = {
    AWS_TERRAFORM_ROLE_ARN = aws_iam_role.terraform_ci.arn
    TF_STATE_BUCKET        = aws_s3_bucket.terraform_state.bucket
    TF_LOCK_TABLE          = aws_dynamodb_table.terraform_lock.name
    AWS_REGION             = var.aws_region
  }
}
