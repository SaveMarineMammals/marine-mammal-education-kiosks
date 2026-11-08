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

module "admin_alert" {
  count  = var.enable_admin_alert ? 1 : 0
  source = "../../modules/admin-alert"

  name_prefix                = local.name_prefix
  alert_ingest_token         = var.alert_ingest_token
  sent_api_key               = var.sent_api_key
  sent_template_id           = var.sent_template_id
  sent_template_name         = var.sent_template_name
  alert_sms_to               = var.alert_sms_to
  alert_email_to             = var.alert_email_to
  ses_from_email             = var.ses_from_email
  create_ses_email_identity  = var.create_ses_alert_identity
  tags                       = local.common_tags
}
