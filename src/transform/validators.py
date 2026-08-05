from pyspark.sql import DataFrame


class TransformValidationError(Exception):
    pass

#comparison of two columns raws and curateds
def validators_no_parse_failures(
    df: DataFrame,raw_col: str,curated_col: str,dataset_name: str) -> None:

    failure_counts = df.filter(
        df[raw_col].isNotNull() & df[curated_col].isNull()
    ).count()

    if failure_counts > 0:
        raise TransformValidationError(
            f"[{dataset_name}] {failure_counts} row(s) had a non-null "
            f"'{raw_col}' value that failed to parse into a '{curated_col}' value. "
            f"This likely means the raw data was not in the expected format. "
            f"Aborting write to curated S3."
        )

# validates that all required columns are not null
def validators_required_columns_not_null(
    df: DataFrame,required_columns: list[str],dataset_name: str) -> None:

    for col_name in required_columns:
        null_count = df.filter(df[col_name].isNull()).count()
        if null_count > 0:
            raise TransformValidationError(
                f"[{dataset_name}] Required column '{col_name}' has {null_count} null value(s). "
                f"Aborting write to curated S3."
            )