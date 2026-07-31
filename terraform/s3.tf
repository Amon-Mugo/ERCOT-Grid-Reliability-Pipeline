resource "aws_s3_bucket" "ercot_grid_pipeline_raw" {
    bucket="ercot-grid-pipeline-raw"
    tags = {
        Project     = "ercot-grid-reliability-pipeline"
        Layer       = "raw"
        Environment = "prod"
    }
}

resource "aws_s3_bucket_ownership_controls" "ercot_grid_pipeline_raw" {
    bucket = aws_s3_bucket.ercot_grid_pipeline_raw.id
    rule {
        object_ownership = "BucketOwnerEnforced"
    }
}
resource "aws_s3_bucket_public_access_block" "ercot_grid_pipeline_raw" {
    bucket                  = aws_s3_bucket.ercot_grid_pipeline_raw.id
    block_public_acls       = true
    block_public_policy     = true
    ignore_public_acls      = true
    restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "ercot_grid_pipeline_raw" {
    bucket =aws_s3_bucket.ercot_grid_pipeline_raw.id
    versioning_configuration {
        status ="Enabled"
    }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ercot_grid_pipeline_raw" {
    bucket = aws_s3_bucket.ercot_grid_pipeline_raw.id

    rule {
        apply_server_side_encryption_by_default{
            sse_algorithm = "AES256"# "aws:kms" encryption key
        }
    }
}

resource "aws_s3_bucket_lifecycle_configuration" "ercot_grid_pipeline_raw" {
    depends_on = [aws_s3_bucket_versioning.ercot_grid_pipeline_raw] # wait for versioning to be enabled
    bucket     = aws_s3_bucket.ercot_grid_pipeline_raw.id

    rule{
        id ="delete-old-versions"
        status = "Enabled"
        filter {}
        noncurrent_version_expiration {
            noncurrent_days = 60
        }
        abort_incomplete_multipart_upload{
            days_after_initiation = 5
        }
        expiration{
            expired_object_delete_marker = true
        }
    }
}

#curated addons to make the infractructure more polished and separate

resource "aws_s3_bucket" "ercot_grid_pipeline_curated"{
    bucket = "ercot-grid-pipeline-curated"
    tags={
        Project      ="ercot-grid-reliability-pipeline"
        Layer        ="curated"
        Environment  = "prod"
    }
}

resource "aws_s3_bucket_ownership_controls" "ercot_grid_pipeline_curated"{
    bucket =aws_s3_bucket.ercot_grid_pipeline_curated.id
    rule {
        object_ownership ="BucketOwnerEnforced"
    }
}

resource "aws_s3_bucket_public_access_block" "ercot_grid_pipeline_curated"{
    bucket = aws_s3_bucket.ercot_grid_pipeline_curated.id
    block_public_acls       = true
    block_public_policy     = true
    ignore_public_acls     = true
    restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "ercot_grid_pipeline_curated"{
    bucket =aws_s3_bucket.ercot_grid_pipeline_curated.id
    versioning_configuration{
        status ="Enabled"
    }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ercot_grid_pipeline_curated"{
    bucket = aws_s3_bucket.ercot_grid_pipeline_curated.id
    rule{
        apply_server_side_encryption_by_default{
            sse_algorithm = "AES256"# "aws:kms" encryption key

        }
    }
}

resource "aws_s3_bucket_lifecycle_configuration" "ercot_grid_pipeline_curated"{
    bucket     = aws_s3_bucket.ercot_grid_pipeline_curated.id
    rule{
        id="abort-incomplete-multipart-uploads"
        status = "Enabled"
        filter{}
        abort_incomplete_multipart_upload{
            days_after_initiation = 5
        }
    }
}