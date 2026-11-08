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
