terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # No backend block yet — using local state for the initial apply.
  # Once ercot-grid-pipeline-raw/curated exist, we'll add an S3 backend
  # (a third bucket, or a dedicated prefix in curated) and migrate state.
}

provider "aws" {
  region  = "us-east-1"
  profile = "data-corp-admin"
}

