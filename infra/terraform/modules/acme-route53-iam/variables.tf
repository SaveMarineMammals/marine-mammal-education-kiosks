variable "name_prefix" {
  description = "Prefix for IAM user name when user_name is empty"
  type        = string
}

variable "user_name" {
  description = "Optional explicit IAM user name"
  type        = string
  default     = ""
}

variable "hosted_zone_id" {
  description = "Route 53 hosted zone ID Caddy may modify (kiosks.local zone)"
  type        = string
}

variable "create_access_key" {
  description = "Create an access key (secret stored in Terraform state). Disable to manage keys out of band."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags for the IAM user"
  type        = map(string)
  default     = {}
}
