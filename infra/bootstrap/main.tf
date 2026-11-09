locals {
  account_id        = data.aws_caller_identity.current.account_id
  state_bucket_name = var.state_bucket_name != "" ? var.state_bucket_name : "${var.project_name}-terraform-state-${local.account_id}"
  common_tags = merge(var.tags, {
    Project   = var.project_name
    Component = "terraform-bootstrap"
    ManagedBy = "terraform"
  })
  create_oidc_provider = var.github_oidc_provider_arn == ""
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = local.state_bucket_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "terraform_lock" {
  name         = "${var.project_name}-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = local.common_tags
}

data "tls_certificate" "github" {
  count = local.create_oidc_provider ? 1 : 0
  url   = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  count = local.create_oidc_provider ? 1 : 0

  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com",
  ]

  thumbprint_list = distinct([
    for cert in data.tls_certificate.github[0].certificates :
    replace(cert.sha1_fingerprint, ":", "")
  ])

  tags = local.common_tags
}

locals {
  github_oidc_provider_arn = local.create_oidc_provider ? aws_iam_openid_connect_provider.github[0].arn : var.github_oidc_provider_arn
  # GitHub immutable OIDC subjects (2025+): repo:ORG@ORG_ID/REPO@REPO_ID:...
  # CloudTrail example: repo:SaveMarineMammals@293631734/marine-mammal-education-kiosks@1305123252:pull_request
  github_owner_name = split("/", var.github_repository)[0]
  github_repo_name  = split("/", var.github_repository)[1]
  github_oidc_sub_immutable = "repo:${local.github_owner_name}@${var.github_org_id}/${local.github_repo_name}@${var.github_repository_id}:*"
  github_oidc_sub_legacy    = "repo:${var.github_repository}:*"
}

data "aws_iam_policy_document" "terraform_ci_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.github_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        local.github_oidc_sub_immutable,
        local.github_oidc_sub_legacy,
      ]
    }
  }
}

resource "aws_iam_role" "terraform_ci" {
  name               = "${var.project_name}-terraform-ci"
  assume_role_policy = data.aws_iam_policy_document.terraform_ci_assume.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "terraform_ci" {
  statement {
    sid    = "TerraformState"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.terraform_state.arn,
      "${aws_s3_bucket.terraform_state.arn}/*",
    ]
  }

  statement {
    sid    = "TerraformLock"
    effect = "Allow"
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem",
    ]
    resources = [aws_dynamodb_table.terraform_lock.arn]
  }

  statement {
    sid    = "ManageDnsAndAcmeIam"
    effect = "Allow"
    actions = [
      "route53:*",
      "iam:GetUser",
      "iam:GetUserPolicy",
      "iam:ListUserPolicies",
      "iam:ListAttachedUserPolicies",
      "iam:ListAccessKeys",
      "iam:CreateUser",
      "iam:DeleteUser",
      "iam:TagUser",
      "iam:UntagUser",
      "iam:PutUserPolicy",
      "iam:DeleteUserPolicy",
      "iam:CreateAccessKey",
      "iam:DeleteAccessKey",
      "iam:UpdateAccessKey",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListRolePolicies",
      "iam:PassRole",
      "sts:GetCallerIdentity",
    ]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = [var.aws_region, "us-east-1"]
    }
  }

  # Route 53 and some IAM APIs are global; still allow without region condition.
  statement {
    sid    = "Route53Global"
    effect = "Allow"
    actions = [
      "route53:*",
      "iam:GetUser",
      "iam:CreateUser",
      "iam:DeleteUser",
      "iam:TagUser",
      "iam:UntagUser",
      "iam:PutUserPolicy",
      "iam:DeleteUserPolicy",
      "iam:GetUserPolicy",
      "iam:ListUserPolicies",
      "iam:ListAccessKeys",
      "iam:CreateAccessKey",
      "iam:DeleteAccessKey",
      "iam:UpdateAccessKey",
    ]
    resources = ["*"]
  }

  # admin-alert Lambda + SES From identity (IAM role APIs are global).
  statement {
    sid    = "AdminAlertIamRoles"
    effect = "Allow"
    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:PassRole",
      "iam:ListInstanceProfilesForRole",
    ]
    resources = [
      "arn:aws:iam::${local.account_id}:role/${var.project_name}-*-admin-alert-role",
    ]
  }

  # Broad lambda:* avoids provider whack-a-mole (e.g. GetFunctionCodeSigningConfig
  # after CreateFunction). Scope remains this CI role only.
  statement {
    sid    = "AdminAlertLambdaSesLogs"
    effect = "Allow"
    actions = [
      "lambda:*",
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:DescribeLogGroups",
      "logs:PutRetentionPolicy",
      "logs:DeleteRetentionPolicy",
      "logs:ListTagsForResource",
      "logs:TagResource",
      "logs:UntagResource",
      "ses:VerifyEmailIdentity",
      "ses:DeleteIdentity",
      "ses:GetIdentityVerificationAttributes",
      "ses:ListIdentities",
      "ses:GetSendQuota",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "terraform_ci" {
  name   = "${var.project_name}-terraform-ci"
  role   = aws_iam_role.terraform_ci.id
  policy = data.aws_iam_policy_document.terraform_ci.json
}
