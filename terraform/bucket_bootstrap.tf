# backup if you accidentally delete this file

resource "aws_s3_bucket" "tfstate" {
    bucket="ercot-grid-pipeline-tfstate"
    lifecycle {
        prevent_destroy=true
    }
    tags= {
        Project=var.project_name
        Purpose="Terraform State"
        ManagedBy="Terraform"
    }
}

#versioning
resource "aws_s3_bucket_versioning" "tfstate" {
    bucket=aws_s3_bucket.tfstate.id
    versioning_configuration{
        status="Enabled"
    }
}

#secuity

resource "aws_s3_bucket_public_access_block" "tfstate"{
    bucket=aws_s3_bucket.tfstate.id
    block_public_acls=true
    block_public_policy=true
    ignore_public_acls=true
    restrict_public_buckets=true
}

#encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
    bucket=aws_s3_bucket.tfstate.id
    rule{
        apply_server_side_encryption_by_default{
            sse_algorithm="AES256"
        }
    }
}
