from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit, to_timestamp
from src.transform.validators import (
    validators_required_columns_not_null,
    validators_no_parse_failures)

EIA_PERIOD_FORMAT = "yyyy-MM-dd'T'HH"


def transform_interchange(df: DataFrame, ingestion_date: str) -> DataFrame:
    with_parsed = df.withColumn(
        "parsed_period", to_timestamp(col("period"), EIA_PERIOD_FORMAT)
    ).withColumn("parsed_value", col("value").cast("double"))

    validators_no_parse_failures(with_parsed, "period", "parsed_period", "interchange")
    validators_no_parse_failures(with_parsed, "value", "parsed_value", "interchange")

    curated = with_parsed.withColumn("ingestion_date", lit(ingestion_date).cast("date")) .select(
        col("respondent"),
        col("parsed_period").alias("period"),
        col("parsed_value").alias("value"),
        col("value-units").alias("value_units"),
        col("ingestion_date"),
    )

    validators_required_columns_not_null(
        curated,
        required_columns=["respondent", "period", "ingestion_date"],
        dataset_name="interchange",
    )
    return curated
