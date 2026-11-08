locals {
  parent_domain   = var.parent_domain
  belize_domain   = "belize.${var.parent_domain}"
  kiosks_domain   = "kiosks.local.${local.belize_domain}"
  cms_record_name = "server.${local.kiosks_domain}"
}

data "aws_route53_zone" "parent" {
  name         = local.parent_domain
  private_zone = false
}

resource "aws_route53_zone" "belize" {
  name    = local.belize_domain
  comment = "MMEK Belize facility DNS (${local.belize_domain})"

  tags = merge(var.tags, {
    Name = local.belize_domain
    Tier = "facility-country"
  })
}

resource "aws_route53_record" "belize_ns" {
  zone_id = data.aws_route53_zone.parent.zone_id
  name    = local.belize_domain
  type    = "NS"
  ttl     = var.delegation_ttl
  records = aws_route53_zone.belize.name_servers
}

resource "aws_route53_zone" "kiosks" {
  name    = local.kiosks_domain
  comment = "MMEK kiosk LAN DNS + Let's Encrypt DNS-01 (${local.kiosks_domain})"

  tags = merge(var.tags, {
    Name = local.kiosks_domain
    Tier = "facility-kiosks"
  })
}

resource "aws_route53_record" "kiosks_ns" {
  zone_id = aws_route53_zone.belize.zone_id
  name    = local.kiosks_domain
  type    = "NS"
  ttl     = var.delegation_ttl
  records = aws_route53_zone.kiosks.name_servers
}

resource "aws_route53_record" "cms_a" {
  count = var.cms_server_ipv4 != "" ? 1 : 0

  zone_id = aws_route53_zone.kiosks.zone_id
  name    = local.cms_record_name
  type    = "A"
  ttl     = var.record_ttl
  records = [var.cms_server_ipv4]
}

resource "aws_route53_record" "cms_aaaa" {
  count = var.cms_server_ipv6 != "" ? 1 : 0

  zone_id = aws_route53_zone.kiosks.zone_id
  name    = local.cms_record_name
  type    = "AAAA"
  ttl     = var.record_ttl
  records = [var.cms_server_ipv6]
}
