variable "name_prefix" {
  description = "Resource name prefix (e.g. mmek-production)"
  type        = string
}

variable "alert_ingest_token" {
  description = "Bearer token hosts present to the Function URL"
  type        = string
  sensitive   = true
}

variable "sent_api_key" {
  description = "Sent.dm Customer API key (x-api-key)"
  type        = string
  sensitive   = true
}

variable "sent_template_id" {
  description = "Sent.dm template UUID (adm-siteerror default)"
  type        = string
  default     = "5e3a2913-647a-408c-a3fe-d9cd3d103641"
}

variable "sent_template_name" {
  description = "Sent.dm template name (optional if id set)"
  type        = string
  default     = "adm-siteerror"
}

variable "alert_sms_to" {
  description = "Comma-separated E.164 admin phone numbers"
  type        = string
}

variable "alert_email_to" {
  description = "Comma-separated admin email addresses"
  type        = string
}

variable "ses_from_email" {
  description = "Verified SES From address"
  type        = string
}

variable "create_ses_email_identity" {
  description = "Create aws_ses_email_identity for ses_from_email (set true only if Terraform should own verification)"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Extra tags"
  type        = map(string)
  default     = {}
}
