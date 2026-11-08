output "lambda_function_name" {
  value = aws_lambda_function.alert.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.alert.arn
}

output "alert_lambda_url" {
  description = "Function URL for /etc/mmek/alert.env ALERT_LAMBDA_URL"
  value       = aws_lambda_function_url.alert.function_url
}

output "ses_from_email" {
  value = var.ses_from_email
}
