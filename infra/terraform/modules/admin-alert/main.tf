terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4"
    }
  }
}

locals {
  function_name = "${var.name_prefix}-admin-alert"
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/src/handler.py"
  output_path = "${path.module}/build/admin-alert.zip"
}

data "aws_iam_policy_document" "assume_lambda" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
  tags = merge(var.tags, {
    Name    = "${local.function_name}-role"
    Purpose = "mmek-admin-alert"
  })
}

data "aws_iam_policy_document" "lambda" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }

  statement {
    sid       = "SesSend"
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "${local.function_name}-policy"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda.json
}

resource "aws_ses_email_identity" "from" {
  count = var.create_ses_email_identity ? 1 : 0
  email = var.ses_from_email
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_lambda_function" "alert" {
  function_name = local.function_name
  role          = aws_iam_role.lambda.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  filename      = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout       = 30
  memory_size   = 128

  environment {
    variables = {
      ALERT_INGEST_TOKEN = var.alert_ingest_token
      SENT_API_KEY       = var.sent_api_key
      SENT_TEMPLATE_ID   = var.sent_template_id
      SENT_TEMPLATE_NAME = var.sent_template_name
      ALERT_SMS_TO       = var.alert_sms_to
      ALERT_EMAIL_TO     = var.alert_email_to
      SES_FROM_EMAIL     = var.ses_from_email
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.lambda,
  ]

  tags = merge(var.tags, {
    Name    = local.function_name
    Purpose = "mmek-admin-alert"
  })

  lifecycle {
    precondition {
      condition = (
        var.alert_ingest_token != "" &&
        var.sent_api_key != "" &&
        var.alert_sms_to != "" &&
        var.alert_email_to != "" &&
        var.ses_from_email != "" &&
        (var.sent_template_id != "" || var.sent_template_name != "")
      )
      error_message = "admin-alert requires ingest token, Sent API key, SMS/email recipients, SES from, and a Sent template id or name."
    }
  }
}

resource "aws_lambda_function_url" "alert" {
  function_name      = aws_lambda_function.alert.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["authorization", "content-type"]
  }
}

resource "aws_lambda_permission" "function_url" {
  statement_id           = "FunctionURLAllowPublicInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.alert.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}
