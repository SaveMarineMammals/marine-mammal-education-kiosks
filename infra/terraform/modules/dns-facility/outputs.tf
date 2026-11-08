output "parent_zone_id" {
  description = "Existing parent hosted zone ID"
  value       = data.aws_route53_zone.parent.zone_id
}

output "belize_domain" {
  description = "Belize facility zone apex"
  value       = aws_route53_zone.belize.name
}

output "belize_zone_id" {
  description = "Belize facility hosted zone ID"
  value       = aws_route53_zone.belize.zone_id
}

output "belize_name_servers" {
  description = "NS set for belize.<parent> (also written into the parent zone)"
  value       = aws_route53_zone.belize.name_servers
}

output "kiosks_domain" {
  description = "Kiosks zone apex (Let's Encrypt DNS-01 target)"
  value       = aws_route53_zone.kiosks.name
}

output "kiosks_zone_id" {
  description = "Kiosks hosted zone ID for Caddy ACME (AWS_HOSTED_ZONE_ID)"
  value       = aws_route53_zone.kiosks.zone_id
}

output "kiosks_name_servers" {
  description = "NS set for kiosks.local.belize.<parent>"
  value       = aws_route53_zone.kiosks.name_servers
}

output "cms_hostname" {
  description = "FQDN used by players / Caddy for the CMS"
  value       = "server.${aws_route53_zone.kiosks.name}"
}
