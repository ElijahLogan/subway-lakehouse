locals {
  name = "subway-lake-${var.env}"
}


resource "aws_ssm_parameter" "databricks_token" {
  name  = "/subway-lake/${var.env}/databricks_token"
  type  = "SecureString" # standard tier + AWS-managed key = free
  value = "set-me"
  lifecycle { ignore_changes = [value] }
}

resource "aws_ssm_parameter" "dd_api_key" {
  name  = "/subway-lake/${var.env}/dd_api_key"
  type  = "SecureString"
  value = "set-me"
  lifecycle { ignore_changes = [value] }
}

resource "aws_cloudwatch_log_group" "poller" {
  name              = "/aws/lambda/${local.name}-poller"
  retention_in_days = 3 # logs are the sneaky cost; keep them short
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "poller" {
  name               = "${local.name}-poller"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "poller" {
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.poller.arn}:*"]
  }
  statement {
    actions   = ["ssm:GetParameter"]
    resources = [aws_ssm_parameter.databricks_token.arn, aws_ssm_parameter.dd_api_key.arn]
  }
}

resource "aws_iam_role_policy" "poller" {
  role   = aws_iam_role.poller.id
  policy = data.aws_iam_policy_document.poller.json
}


# data "archive_file" "poller" {
#   type        = "zip"
#   source_dir  = "${path.module}/../../../ingestion"
#   output_path = "${path.module}/../../../build/layer.zip"
#   excludes    = ["tests", "requirements.txt"]
# }

# # Dependencies: built by `make layer`, only when requirements change
# resource "aws_lambda_layer_version" "deps" {
#   layer_name               = "subway-lake-deps"
#   filename                 = "${path.module}/../../../build/layer.zip"
#   source_code_hash         = filebase64sha256("${path.module}/../../../build/layer.zip")
#   compatible_runtimes      = ["python3.12"]
#   compatible_architectures = ["arm64"]
# }

resource "aws_lambda_function" "poller" {
  function_name    = "${local.name}-poller"
  role             = aws_iam_role.poller.arn
  filename         = var.lambda_zip
  source_code_hash = filebase64sha256(var.lambda_zip)
  handler          = "mta_ingest.handler.lambda_handler"
  runtime          = "python3.12"
  architectures    = ["arm64"] # ~20% cheaper per GB-second than x86
  memory_size      = 256
  timeout          = 50 # must finish before the next 1-minute tick

  # Never run two polls at once (also caps runaway cost). Reserved concurrency is free.
  reserved_concurrent_executions = 1

  environment {
    variables = {
      ENV                    = var.env
      DATABRICKS_HOST        = var.databricks_host
      VOLUME_PATH            = var.volume_path
      DATABRICKS_TOKEN_PARAM = aws_ssm_parameter.databricks_token.name
      DD_SITE                = var.dd_site
    }
  }

  depends_on = [aws_cloudwatch_log_group.poller]
}


