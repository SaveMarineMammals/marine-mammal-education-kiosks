output "belize_domain" {
  value = module.dns_facility.belize_domain
}

output "belize_zone_id" {
  value = module.dns_facility.belize_zone_id
}

output "belize_name_servers" {
  value = module.dns_facility.belize_name_servers
}

output "kiosks_domain" {
  value = module.dns_facility.kiosks_domain
}

output "kiosks_zone_id" {
  description = "Set AWS_HOSTED_ZONE_ID in /etc/mmek/caddy-acme.env"
  value       = module.dns_facility.kiosks_zone_id
}

output "kiosks_name_servers" {
  value = module.dns_facility.kiosks_name_servers
}

output "cms_hostname" {
  value = module.dns_facility.cms_hostname
}

output "acme_iam_user_name" {
  value = module.acme_route53_iam.iam_user_name
}

output "acme_access_key_id" {
  value = module.acme_route53_iam.access_key_id
}

output "acme_secret_access_key" {
  description = "Sensitive — terraform output -raw acme_secret_access_key"
  value       = module.acme_route53_iam.secret_access_key
  sensitive   = true
}

output "caddy_acme_env" {
  description = "Non-secret lines for /etc/mmek/caddy-acme.env (add secret separately)"
  value = {
    AWS_ACCESS_KEY_ID  = module.acme_route53_iam.access_key_id
    AWS_REGION         = var.aws_region
    AWS_HOSTED_ZONE_ID = module.dns_facility.kiosks_zone_id
  }
}
