import pytest

from pyspark.sql import Row,SparkSession
from pyspark.sql.types import StringType, StructField, StructType
from src.transform.validators import (TransformValidationError,validators_no_parse_failures,validators_required_columns_not_null)

class TestValidatorsNoParseFailures:
    def test_passes_when_all_non_null_raw_values_parsed(self,spark: SparkSession):
        df=spark.createDataFrame(
            [
                Row(raw="2026-08-01T14",parsed="2026-08-01 14:00:00"),
                Row(raw="2026-08-01T15",parsed="2026-08-01 15:00:00"),

            ])
        
        validators_no_parse_failures(df,"raw","parsed","demand")

    # test raw null that produce null parased
    def test_parsed_when_null_raw_values_have_null_parsed_values(self,spark: SparkSession):
        df=spark.createDataFrame([
            Row(raw=None,parsed=None),
            Row(raw="2026-08-01T14",parsed="2026-08-01 14:00:00"),
        ])
        validators_no_parse_failures(df,"raw","parsed","demand")

    # test raw non-null that produce null parased

    def test_raise_when_non_null_raw_value_has_null_parsed_value(self,spark: SparkSession):
        df=spark.createDataFrame([
            Row(raw="not-real-timestamp",parsed=None),
            Row(raw="2026-08-01T14",parsed="2026-08-01 14:00:00"),

        ])
        with pytest.raises(TransformValidationError,match="1 row"):
            validators_no_parse_failures(df,"raw","parsed","demand")

    #check multiple failures more than 1 row fails and displays the error message

    def test_error_message_includes_dataset_name_and_failure_count(self,spark:SparkSession):
        # Explicit schema needed here: every row has parsed=None, so Spark
        # can't infer a type for that column from the data alone and raises
        # CANNOT_DETERMINE_TYPE without one.
        schema = StructType([
            StructField("raw", StringType(), True),
            StructField("parsed", StringType(), True),
        ])
        df=spark.createDataFrame([
            ("bad-1", None),
            ("bad-2", None),
        ], schema=schema)
        with pytest.raises(TransformValidationError) as exc_info:
            validators_no_parse_failures(df,"raw","parsed","interchange")

        message=str(exc_info.value)
        assert "interchange" in message #check dataset name is in message
        assert "2" in message #check failure count is in message

class TestValidatorsRequiredColumnsNotNull:
    def test_passes_when_required_columns_have_no_nulls(self, spark: SparkSession):
        df=spark.createDataFrame([
            Row(respondent="ERCO",period="2026-08-01T14"),
            Row(respondent="ERCO",period="2026-08-01T15"),
        ])
        validators_required_columns_not_null(df,required_columns=["respondent","period"],dataset_name="demand")


    #checks if one required column has null values
    def test_raise_when_a_required_column_has_a_null(self,spark:SparkSession):
        df=spark.createDataFrame([
            Row(respondent="ERCO",period="2026-08-01T14"),
            Row(respondent=None,period="2026-08-01T15"),
        ])
        with pytest.raises(TransformValidationError,match="respondent"):
            validators_required_columns_not_null(df,required_columns=["respondent","period"],dataset_name="demand")

    #checks if multiple required columns have null values and error message includes all columns
    def test_error_message_includes_dataset_name_column_and_null_count(self,spark:SparkSession):
        df=spark.createDataFrame([
            Row(respondent=None,period="2026-08-01T14"),
            Row(respondent=None,period="2026-08-01T15"),
            Row(respondent="ERCO",period="2026-08-01T16"),
        ])
        with pytest.raises(TransformValidationError) as exc_info:
            validators_required_columns_not_null(df,required_columns=["respondent"],dataset_name="generation")

        message=str(exc_info.value)
        assert "generation" in message #check dataset name is in message
        assert "respondent" in message #check column name is in message
        assert "2" in message #check null count is in message

    #itterates all columns and not the first only
    def test_check_all_required_columns_not_just_the_first(self,spark:SparkSession):
        df=spark.createDataFrame([
            Row(fromba="ERCO",toba=None),
            Row(fromba="ERCO",toba="SPP"),
        ])

        with pytest.raises(TransformValidationError,match="toba"):
            validators_required_columns_not_null(df,required_columns=["fromba","toba"],dataset_name="interchange")
