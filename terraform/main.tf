terraform {
  required_version = ">=1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  #backend  will leave in aws cloud rather than local
  backend "s3" {
    bucket       = "ercot-grid-pipeline-tfstate"           #bucket name
    key          = "ercot-grid-pipeline/terraform.tfstate" #where it will be stored
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true

  }
}
provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile != "" ? var.aws_profile : null
}