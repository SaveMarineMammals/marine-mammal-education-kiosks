variable "parent_domain" {
  description = "Existing parent public hosted zone name (must already exist in Route 53)"
  type        = string
  default     = "savemarinemammals.com"
}

variable "cms_server_ipv4" {
  description = "Optional A record for server.kiosks.local.belize.<parent> (CMS host). Empty skips the record."
  type        = string
  default     = ""
}

variable "cms_server_ipv6" {
  description = "Optional AAAA record for the CMS hostname. Empty skips the record."
  type        = string
  default     = ""
}

variable "delegation_ttl" {
  description = "TTL for NS delegation records"
  type        = number
  default     = 300
}

variable "record_ttl" {
  description = "TTL for CMS A/AAAA records"
  type        = number
  default     = 60
}

variable "tags" {
  description = "Tags applied to hosted zones"
  type        = map(string)
  default     = {}
}
