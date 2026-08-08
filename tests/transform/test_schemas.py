import pytest
from pyspark.sql.types import(
    DateType,
    DoubleType,
    StringType,
    TimestampType,
)

from src.transform.schemas import (
    CURATED_DEMAND_SCHEMA,
    CURATED_GENERATION_SCHEMA,
    CURATED_INTERCHANGE_SCHEMA,
    RAW_DEMAND_SCHEMA,
    RAW_GENERATION_SCHEMA,
    RAW_INTERCHANGE_SCHEMA,
)

#raw schemas setup

RAW_SCHEMAS= [
    pytest.param(
        RAW_DEMAND_SCHEMA,
        ["respondent", "period", "value", "value-units"], #fields
        ["respondent","period"], # cannot be null
        ["value","value-units"], # can be null
        id="raw_demand",
    ),

    pytest.param(
        RAW_INTERCHANGE_SCHEMA,
        ["fromba", "toba", "period", "value", "value-units"], #fields
        ["fromba","toba","period"], # cannot be null
        ["value","value-units"], # can be null
        id="raw_interchange",
    ),

    pytest.param(
        RAW_GENERATION_SCHEMA,
        ["respondent", "fueltype", "period", "value", "value-units"], #fields
        ["respondent","fueltype","period"], # cannot be null
        ["value","value-units"], # can be null
        id="raw_generation",
    ),
]

@pytest.mark.parametrize("schema,expected_fields,non_nullable_fields,nullable_fields",RAW_SCHEMAS)
#acts as a connection between raw schema and curated schema

def test_raw_schemas(schema,expected_fields,non_nullable_fields,nullable_fields):
    assert schema.fieldNames() == expected_fields # comaprison of shecmas.py file and our test file
    by_name={f.name:f for f in schema.fields} # built the dict for easy lookup

    for field in schema.fields:
        assert field.dataType==StringType()

    for col in non_nullable_fields:
        assert by_name[col].nullable is False

    for col in nullable_fields:
        assert by_name[col].nullable is True


#curated schemas setup
class TestCuratedDemandSchema:
    EXPECTED_TYPES={
        "respondent":StringType(),
        "period":TimestampType(),
        "value":DoubleType(),
        "value_units":StringType(),
        "ingestion_date":DateType(),
    }

    def test_field_name_and_order(self):
        assert CURATED_DEMAND_SCHEMA.fieldNames()== list(self.EXPECTED_TYPES.keys())

    def test_field_types(self):
        actual_types={f.name:f.dataType for f in CURATED_DEMAND_SCHEMA.fields}
        assert actual_types== self.EXPECTED_TYPES

    def test_nullability(self):
        by_name={f.name:f for f in CURATED_DEMAND_SCHEMA.fields}
        assert by_name["respondent"].nullable is False
        assert by_name["period"].nullable is False
        assert by_name["ingestion_date"].nullable is False
        assert by_name["value"].nullable is True
        assert by_name["value_units"].nullable is True

class TestCuratedInterchangeSchema:
    EXPECTED_TYPES={
        "fromba":StringType(),
        "toba":StringType(),
        "period":TimestampType(),
        "value":DoubleType(),
        "value_units":StringType(),
        "ingestion_date":DateType(),
    }

    def test_field_name_and_order(self):
        assert CURATED_INTERCHANGE_SCHEMA.fieldNames()== list(self.EXPECTED_TYPES.keys())

    def test_field_types(self):
        actual_types={f.name:f.dataType for f in CURATED_INTERCHANGE_SCHEMA.fields}
        assert actual_types== self.EXPECTED_TYPES

    def test_nullability(self):
        by_name={f.name:f for f in CURATED_INTERCHANGE_SCHEMA.fields}
        assert by_name["fromba"].nullable is False
        assert by_name["toba"].nullable is False
        assert by_name["period"].nullable is False
        assert by_name["ingestion_date"].nullable is False
        assert by_name["value"].nullable is True
        assert by_name["value_units"].nullable is True

class TestCuratedGenerationSchema:
    EXPECTED_TYPES={
        "respondent":StringType(),
        "fuel_type":StringType(),
        "period":TimestampType(),
        "value":DoubleType(),
        "value_units":StringType(),
        "ingestion_date":DateType(),
    }

    def test_field_name_and_order(self):
        assert CURATED_GENERATION_SCHEMA.fieldNames() == list(self.EXPECTED_TYPES.keys())

    def test_field_types(self):
        actual_types={f.name:f.dataType for f in CURATED_GENERATION_SCHEMA.fields}
        assert actual_types== self.EXPECTED_TYPES

    def test_nullability(self):
        by_name={f.name:f for f in CURATED_GENERATION_SCHEMA.fields}
        assert by_name["respondent"].nullable is False
        assert by_name["fuel_type"].nullable is False
        assert by_name["period"].nullable is False
        assert by_name["ingestion_date"].nullable is False
        assert by_name["value"].nullable is True
        assert by_name["value_units"].nullable is True