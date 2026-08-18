import sys
from datetime import date, datetime, timedelta, timezone

from pyspark.sql import DataFrame, SparkSession

from src.transform.demand_transform import transform_demand
from src.transform.generation_transform import transform_generation
from src.transform.interchange_transform import transform_interchange
from src.transform.schemas import (
    RAW_DEMAND_SCHEMA,
    RAW_INTERCHANGE_SCHEMA,
    RAW_GENERATION_SCHEMA,
)
from src.transform.spark_session import get_spark_session
from src.transform.validators import TransformValidationError

RAW_BUCKET = "ercot-grid-pipeline-raw"
CURATED_BUCKET = "ercot-grid-pipeline-curated"

DATASETS = {
    "demand": (RAW_DEMAND_SCHEMA, transform_demand),
    "interchange": (RAW_INTERCHANGE_SCHEMA, transform_interchange),
    "generation_by_fuel": (RAW_GENERATION_SCHEMA, transform_generation),
}


def compute_ingestion_date() -> date:
    # computes the date of yesterday's window
    return (datetime.now(timezone.utc) - timedelta(days=1)).date()


def raw_path(dataset: str, ingestion_date: date) -> str:
    return f"s3://{RAW_BUCKET}/{dataset}/dt={ingestion_date.isoformat()}/data.ndjson"


def curated_path(dataset: str, ingestion_date: date) -> str:
    return f"s3://{CURATED_BUCKET}/{dataset}/dt={ingestion_date.isoformat()}/"


def read_raw(spark: SparkSession, dataset: str, schema, ingestion_date: date) -> DataFrame:
    return spark.read.schema(schema).json(raw_path(dataset, ingestion_date))


def write_curated(df: DataFrame, dataset: str, ingestion_date: date) -> None:
    df.write.mode("overwrite").parquet(curated_path(dataset, ingestion_date))


def run(spark: SparkSession, ingestion_date: date) -> list[str]:
    failed: list[str] = []

    for dataset, (schema, transform_fn) in DATASETS.items():
        try:
            raw_df = read_raw(spark, dataset, schema, ingestion_date)
            curated_df = transform_fn(raw_df, ingestion_date)
            write_curated(curated_df, dataset, ingestion_date)

            print(
                f"[run_transform] {dataset}: wrote curated output for {ingestion_date}"
            )

        except TransformValidationError as e:
            print(
                f"[run_transform] {dataset}: VALIDATION FAILED, skipping write — {e}"
            )
            failed.append(dataset)

        except Exception as e:
            print(
                f"[run_transform] {dataset}: UNEXPECTED FAILURE, skipping write — {e}"
            )
            failed.append(dataset)

    return failed


def main() -> None:
    ingestion_date = compute_ingestion_date()
    spark = get_spark_session()

    try:
        failed = run(spark, ingestion_date)
    finally:
        spark.stop()

    if failed:
        print(f"[run_transform] FAILED datasets: {', '.join(failed)}")
        sys.exit(1)

    print(
        f"[run_transform] all datasets transformed successfully for {ingestion_date}"
    )


if __name__ == "__main__":
    main()
