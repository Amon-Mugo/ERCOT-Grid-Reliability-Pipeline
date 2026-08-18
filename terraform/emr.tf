#emr is used to manage the spark cluster and track the cluster state and cost

resource "aws_emrserverless_application" "ercot_pyspark" {
  name          = var.emr_app_name
  release_label = "emr-7.1.0"
  type          = "SPARK"
  image_configuration {
    image_uri = "${aws_ecr_repository.ercot_pyspark.repository_url}:${var.emr_image_tag}"
  }
  maximum_capacity {
    cpu    = "4 vCPU"
    memory = "16 GB"

  }
  auto_start_configuration {
    enabled = true # Enables auto start of the cluster
  }
  auto_stop_configuration {
    enabled              = true # Enables auto stop of the cluster
    idle_timeout_minutes = 5    # Stops the cluster if it is idle for 5 minutes
  }
  tags = {
    Project   = "ercot-grid-pipeline"
    ManagedBy = "terraform"

  }
}