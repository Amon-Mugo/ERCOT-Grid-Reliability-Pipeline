data "aws_caller_identity" "current" {}


resource "aws_iam_role" "ercot_ingestion" {
  name = var.ingestion_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  tags = {
    Project = "ercot-grid-reliability-pipeline"
    Purpose = "local-ingestion"
  }
}

resource "aws_iam_policy" "ercot_ingestion_s3_write" {
  name        = "ercot-ingestion-s3-write"
  description = "Write-only access to the ERCOT raw data bucket, scoped to ingestion's actual PutObject usage."
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.ercot_grid_pipeline_raw.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ercot_ingestion_s3_write" {
  role       = aws_iam_role.ercot_ingestion.name
  policy_arn = aws_iam_policy.ercot_ingestion_s3_write.arn
}



resource "aws_iam_role" "ercot_emr_serverless_execution" {
  name = var.emr_execution_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "emr-serverless.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  tags = {
    Project = "ercot-grid-reliability-pipeline"
    Purpose = "emr-serverless-transform"
  }
}

resource "aws_iam_policy" "ercot_emr_serverless_s3_access" {
  name        = "ercot-emr-serverless-s3-access"
  description = "Read raw data from raw bucket, write Parquet/curated output to curated bucket."
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Read access on raw bucket
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.ercot_grid_pipeline_raw.arn,
          "${aws_s3_bucket.ercot_grid_pipeline_raw.arn}/*"
        ]
      },
      # Bucket-level access on curated bucket
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.ercot_grid_pipeline_curated.arn
        ]
      },
      # Full object-level read/write/delete access on curated bucket for
      # PySpark outputs and Spark's temp staging/commit behavior
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.ercot_grid_pipeline_curated.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ercot_emr_serverless_s3_access" {
  role       = aws_iam_role.ercot_emr_serverless_execution.name
  policy_arn = aws_iam_policy.ercot_emr_serverless_s3_access.arn
}


resource "aws_iam_policy" "ercot_emr_serverless_logging" {
  name        = "ercot-emr-serverless-logging"
  description = "Allows EMR Serverless job execution role to write logs to CloudWatch."
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:log-group:/aws/emr-serverless/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ercot_emr_serverless_logging" {
  role       = aws_iam_role.ercot_emr_serverless_execution.name
  policy_arn = aws_iam_policy.ercot_emr_serverless_logging.arn
}