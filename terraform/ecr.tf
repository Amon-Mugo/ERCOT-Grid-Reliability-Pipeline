# Used to store Docker images
resource "aws_ecr_repository" "ercot_pyspark" {
  name                 = var.ecr_repo_name
  image_tag_mutability = "IMMUTABLE" # Ensures tags cannot be overwritten
  force_delete        = false       # Prevents accidental deletion of repo with images

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }

  tags = {
    Project   = "ercot-grid-pipeline"
    ManagedBy = "terraform"
  }
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "ercot_pyspark" {
  repository = aws_ecr_repository.ercot_pyspark.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images older than 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last 7 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
# Allows EMR Serverless to pull the custom Spark image
resource "aws_ecr_repository_policy" "ercot_pyspark_emr_access" {
  repository = aws_ecr_repository.ercot_pyspark.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEMRServerlessPull"
        Effect = "Allow"
        Principal = {
          Service = "emr-serverless.amazonaws.com"
        }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchCheckLayerAvailability",
          "ecr:DescribeImages"
        ]
      }
    ]
  })
}
