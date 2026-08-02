# used to store the variables scatterd across the project

variable "aws_region"{
    description = "AWS region for all resources"
    type = string
    default = "us-east-1"
}

variable "aws_profile"{
    description = "AWS  CLI/SSO profile used for authentication"
    type = string
    default = "data-corp-admin"
}

variable "project_name"{
    description = "Project identifier used for tagging"
    type = string
    default = "ercot-grid-pipeline"
}

variable "ingestion_role_name"{ # used for extraction
    description = "IAM role used for ingestion"
    type = string
    default = "ercot-ingestion"
}

variable "emr_execution_role_name"{
    description = "IAM role name assumed by EMR Serverless jobs"
    type = string
    default = "ercot-emr-serverless-execution"
}

#compute environment and container variables

variable "ecr_repo_name"{
    description = "ECR repository name for Pyspark jobs images"
    type = string
    default = "ercot-pyspark"

}

variable "emr_app_name"{ # EMR Application name
    description = "EMR Application name"
    type = string
    default = "ercot-pyspark"
}

variable "raw_bucket_name" {
    description = "S3 bucket name for raw ingested data"
    type        = string
    default     = "ercot-grid-pipeline-raw"
}

variable "curated_bucket_name" {
    description = "S3 bucket name for curated/transformed data"
    type        = string
    default     = "ercot-grid-pipeline-curated"
}