locals {
  user_name = var.user_name != "" ? var.user_name : "${var.name_prefix}-caddy-acme"
}

resource "aws_iam_user" "acme" {
  name = local.user_name
  path = "/mmek/"
  tags = merge(var.tags, {
    Name    = local.user_name
    Purpose = "caddy-letsencrypt-dns01"
  })
}

data "aws_iam_policy_document" "acme" {
  statement {
    sid    = "ChangeAcmeChallengeRecords"
    effect = "Allow"
    actions = [
      "route53:GetChange",
      "route53:ChangeResourceRecordSets",
      "route53:ListResourceRecordSets",
    ]
    resources = [
      "arn:aws:route53:::hostedzone/${var.hosted_zone_id}",
      "arn:aws:route53:::change/*",
    ]
  }

  statement {
    sid       = "ListZonesForDiscovery"
    effect    = "Allow"
    actions   = ["route53:ListHostedZonesByName"]
    resources = ["*"]
  }
}

resource "aws_iam_user_policy" "acme" {
  name   = "${local.user_name}-route53"
  user   = aws_iam_user.acme.name
  policy = data.aws_iam_policy_document.acme.json
}

resource "aws_iam_access_key" "acme" {
  count = var.create_access_key ? 1 : 0
  user  = aws_iam_user.acme.name
}
