locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    CostCenter  = local.name_prefix
  })
}

module "dns_facility" {
  source = "../../modules/dns-facility"

  parent_domain   = var.parent_domain
  cms_server_ipv4 = var.cms_server_ipv4
  cms_server_ipv6 = var.cms_server_ipv6
  tags            = local.common_tags
}

module "acme_route53_iam" {
  source = "../../modules/acme-route53-iam"

  name_prefix       = local.name_prefix
  hosted_zone_id    = module.dns_facility.kiosks_zone_id
  create_access_key = var.create_acme_access_key
  tags              = local.common_tags
}
