variable "aws_region" {
  description = "AWS region for IAM and API calls (Route 53 is global)"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (used in tags / name prefix)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Short project prefix"
  type        = string
  default     = "mmek"
}

variable "parent_domain" {
  description = "Existing parent hosted zone"
  type        = string
  default     = "savemarinemammals.com"
}

variable "cms_server_ipv4" {
  description = "CMS host IPv4 for server.kiosks.local.belize.<parent>"
  type        = string
  default     = ""
}

variable "cms_server_ipv6" {
  description = "CMS host IPv6 (optional)"
  type        = string
  default     = ""
}

variable "create_acme_access_key" {
  description = "Create IAM access key for Caddy (secret in state)"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Extra tags"
  type        = map(string)
  default     = {}
}

variable "enable_admin_alert" {
  description = "Allow provisioning admin-alert when Sent/SES/recipient vars are also set (via TF_VAR_* or tfvars). Default true so CI secrets alone are enough; set false to force skip."
  type        = bool
  default     = true
}

variable "alert_ingest_token" {
  description = "Bearer token for alert Function URL (hosts)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "sent_api_key" {
  description = "Sent.dm API key for SMS alerts"
  type        = string
  default     = ""
  sensitive   = true
}

variable "sent_template_id" {
  description = "Sent.dm adm-siteerror template UUID"
  type        = string
  default     = "5e3a2913-647a-408c-a3fe-d9cd3d103641"
}

variable "sent_template_name" {
  description = "Sent.dm adm-siteerror template name"
  type        = string
  default     = "adm-siteerror"
}

variable "alert_sms_to" {
  description = "Comma-separated E.164 admin phones for SMS alerts"
  type        = string
  default     = ""
}

variable "alert_email_to" {
  description = "Comma-separated admin emails for SES alerts"
  type        = string
  default     = ""
}

variable "ses_from_email" {
  description = "Verified SES From address for alerts"
  type        = string
  default     = ""
}

variable "create_ses_alert_identity" {
  description = "Create SES email identity for ses_from_email"
  type        = bool
  default     = true
}
