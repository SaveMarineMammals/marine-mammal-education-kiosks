output "iam_user_name" {
  description = "IAM user name for Caddy ACME"
  value       = aws_iam_user.acme.name
}

output "iam_user_arn" {
  description = "IAM user ARN"
  value       = aws_iam_user.acme.arn
}

output "access_key_id" {
  description = "Access key ID (empty when create_access_key is false)"
  value       = var.create_access_key ? aws_iam_access_key.acme[0].id : ""
}

output "secret_access_key" {
  description = "Secret access key — copy to /etc/mmek/caddy-acme.env; never commit"
  value       = var.create_access_key ? aws_iam_access_key.acme[0].secret : ""
  sensitive   = true
}
