# explicitly tell spark to use which columns 
#defines raw columns and also curated columns


from pyspark.sql.types import(
    StructType,
    StructField,
    StringType,
    DoubleType,
    DateType,
    TimestampType,
)

# raw columns  that are not curated which is fetched from api 
#Raw Demand Schema
RAW_DEMAND_SCHEMA=StructType([
    StructField("respondent",StringType(),nullable=False),
    StructField("period",StringType(),nullable=False),
    StructField("value",StringType(),nullable=True),
    StructField("value-units",StringType(),nullable=True),
])

#Raw INterchange Schema

RAW_INTERCHANGE_SCHEMA=StructType([
    StructField("fromba",StringType(),nullable=False),
    StructField("toba",StringType(),nullable=False),
    StructField("period",StringType(),nullable=False),
    StructField("value",StringType(),nullable=True),
    StructField("value-units",StringType(),nullable=True),
])

#Raw Generation Schema
RAW_GENERATION_SCHEMA = StructType(
    [
        StructField("respondent", StringType(), nullable=False),
        StructField("fueltype", StringType(), nullable=False),
        StructField("period", StringType(), nullable=False),
        StructField("value", StringType(), nullable=True),
        StructField("value-units", StringType(), nullable=True),
    ]
)

#curated columns
# curated demand schema
CURATED_DEMAND_SCHEMA = StructType(
    [
        StructField("respondent", StringType(), nullable=False),
        StructField("period", TimestampType(), nullable=False),
        StructField("value", DoubleType(), nullable=True),
        StructField("value_units", StringType(), nullable=True),
        StructField("ingestion_date", DateType(), nullable=False),
    ]
)

# curated interchange schema
CURATED_INTERCHANGE_SCHEMA = StructType(
    [
        StructField("fromba", StringType(), nullable=False),
        StructField("toba", StringType(), nullable=False),
        StructField("period", TimestampType(), nullable=False),
        StructField("value", DoubleType(), nullable=True),
        StructField("value_units", StringType(), nullable=True),
        StructField("ingestion_date", DateType(), nullable=False),
    ]
)

# curated generation schema
CURATED_GENERATION_SCHEMA = StructType(
    [
        StructField("respondent", StringType(), nullable=False),
        StructField("fuel_type", StringType(), nullable=False),
        StructField("period", TimestampType(), nullable=False),
        StructField("value", DoubleType(), nullable=True),
        StructField("value_units", StringType(), nullable=True),
        StructField("ingestion_date", DateType(), nullable=False),
    ]
)

