#used to test the transform functions eg deamnd,interchange,generation
import pytest
from datetime import date,datetime
from pyspark.sql import SparkSession
from pyspark.sql.types import StructField, StructType
from src.transform.demand_transform import transform_demand
from src.transform.generation_transform import transform_generation
from src.transform.interchange_transform import transform_interchange
from src.transform.schemas import (
    CURATED_DEMAND_SCHEMA,
    CURATED_GENERATION_SCHEMA,
    CURATED_INTERCHANGE_SCHEMA,
    RAW_DEMAND_SCHEMA,
    RAW_GENERATION_SCHEMA,
    RAW_INTERCHANGE_SCHEMA,
)

from src.transform.validators import TransformValidationError

INGESTION_DATE="2026-08-08" #date of ingestion


def _with_nullable(schema: StructType, field_name: str) -> StructType:
    """Returns a copy of schema with the given field marked nullable=True,
    so we can construct rows with an illegal null to test validation.
    Needed because PySpark raises at createDataFrame time (not later) if
    you try to put None into a field marked nullable=False."""
    return StructType([
        StructField(f.name, f.dataType, True) if f.name == field_name else f
        for f in schema.fields
    ])


#test fixtures
# Test fixtures
TRANSFORM_CASES = [
    pytest.param(
        transform_demand,
        RAW_DEMAND_SCHEMA,
        CURATED_DEMAND_SCHEMA,
        ("ERCO", "2026-08-01T14", "123.4", "megawatthours"),  
        "respondent",
        id="demand",
    ),
    pytest.param(
        transform_interchange,
        RAW_INTERCHANGE_SCHEMA,
        CURATED_INTERCHANGE_SCHEMA,
        ("ERCO", "2026-08-01T14", "50.0", "megawatthours"),  
        "respondent",
        id="interchange",
    ),
    pytest.param(
        transform_generation,
        RAW_GENERATION_SCHEMA,
        CURATED_GENERATION_SCHEMA,
        ("ERCO", "NG", "2026-08-01T14", "500.0", "megawatthours"),  
        "respondent",
        id="generation",
    ),
]
@pytest.mark.parametrize("transform_fn,raw_schema,curated_schema,valid_row,required_col",TRANSFORM_CASES)
class TestSharedTransformBehavior:
    def test_output_columns_match_curated_schema(self,spark:SparkSession,transform_fn,raw_schema,curated_schema,valid_row,required_col):
        raw_df=spark.createDataFrame([valid_row],schema=raw_schema)
        curated_df=transform_fn(raw_df,INGESTION_DATE)
        assert curated_df.schema.fieldNames()==curated_schema.fieldNames()
        
    #timestamps parsed to datetime
    def test_period_parsed_into_timestamp(self,spark:SparkSession,transform_fn,raw_schema,curated_schema,valid_row,required_col):
        raw_df=spark.createDataFrame([valid_row],schema=raw_schema)
        curated_df=transform_fn(raw_df,INGESTION_DATE)
        result= curated_df.collect()[0]
        # Compare date components only, not the hour — .collect() renders
        # timestamps in the driver JVM's local timezone regardless of
        # spark.sql.session.timeZone, so an exact hour comparison isn't
        # portable across machines.
        assert result["period"].year == 2026
        assert result["period"].month == 8
        assert result["period"].day == 1

    #test  values are cast to double
    def test_value_cast_to_double(self,spark:SparkSession,transform_fn,raw_schema,curated_schema,valid_row,required_col):
        raw_df=spark.createDataFrame([valid_row],schema=raw_schema)
        curated_df=transform_fn(raw_df,INGESTION_DATE)
        result= curated_df.collect()[0]
        assert isinstance (result["value"],float)

    #test if value_units is parsed correctly
    def test_value_units_renamed_to_underscore(self,spark:SparkSession,transform_fn,raw_schema,curated_schema,valid_row,required_col):
        raw_df=spark.createDataFrame([valid_row],schema=raw_schema)
        curated_df=transform_fn(raw_df,INGESTION_DATE)
        assert "value_units" in curated_df.columns
        assert "value-units" not in curated_df.columns
        result= curated_df.collect()[0]
        assert result["value_units"]=="megawatthours"

    #ingestion date casting 
    def test_ingestion_date_added_and_cast_to_date(self,spark:SparkSession,transform_fn,raw_schema,curated_schema,valid_row,required_col):
        raw_df=spark.createDataFrame([valid_row],schema=raw_schema)
        curated_df=transform_fn(raw_df,INGESTION_DATE)
        result= curated_df.collect()[0]
        assert result["ingestion_date"]==date(2026,8,8)

    #invalid timestamps handling
    def test_raises_on_unparseable_period(self,spark:SparkSession,transform_fn,raw_schema,curated_schema,valid_row,required_col):
        bad_row=list(valid_row)
        period_idx=raw_schema.fieldNames().index("period")
        bad_row[period_idx]="not-a-timestamp"
        raw_df=spark.createDataFrame([tuple(bad_row)],schema=raw_schema)
        with pytest.raises(TransformValidationError,match="period"):
            transform_fn(raw_df,INGESTION_DATE)


    #invalid values handling
    def test_raises_on_unparseable_value(self,spark:SparkSession,transform_fn,raw_schema,curated_schema,valid_row,required_col):
        bad_row=list(valid_row)
        value_idx=raw_schema.fieldNames().index("value")
        bad_row[value_idx]="not-a-number"
        raw_df=spark.createDataFrame([tuple(bad_row)],schema=raw_schema)
        with pytest.raises(TransformValidationError,match="value"):
            transform_fn(raw_df,INGESTION_DATE)

    #check null values are handled correctly
    def test_raises_no_null_required_column(self,spark:SparkSession,transform_fn,raw_schema,curated_schema,valid_row,required_col):
        bad_row=list(valid_row)
        required_idx=raw_schema.fieldNames().index(required_col)
        bad_row[required_idx]=None
        relaxed_schema=_with_nullable(raw_schema,required_col)
        raw_df=spark.createDataFrame([tuple(bad_row)],schema=relaxed_schema)
        with pytest.raises(TransformValidationError,match=required_col):
            transform_fn(raw_df,INGESTION_DATE)

#class for specific tests
class TestGenerationSpecificFields:
    def test_fueltype_renamed_to_fuel_type(self, spark: SparkSession):
        raw_df = spark.createDataFrame(
            [("ERCO", "NG", "2026-08-01T14", "500.0", "megawatthours")],
            schema=RAW_GENERATION_SCHEMA,
        )
        curated_df = transform_generation(raw_df, INGESTION_DATE)
        assert "fuel_type" in curated_df.columns
        assert "fueltype" not in curated_df.columns
        result = curated_df.collect()[0]
        assert result["fuel_type"] == "NG"

    def test_raises_when_fuel_type_is_null(self, spark: SparkSession):
        relaxed_schema = _with_nullable(RAW_GENERATION_SCHEMA, "fueltype")
        raw_df = spark.createDataFrame(
            [("ERCO", None, "2026-08-01T14", "500.0", "megawatthours")],
            schema=relaxed_schema,
        )
        with pytest.raises(TransformValidationError, match="fuel_type"):
            transform_generation(raw_df, INGESTION_DATE)
