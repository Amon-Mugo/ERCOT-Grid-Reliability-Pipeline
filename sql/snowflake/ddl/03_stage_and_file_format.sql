--used to grant access used to set up authentication and also to read paquet files stored in s3

USE ROLE ERCOT_ADMIN;
USE DATABASE AWS_SNOWFLAKE_PIPELINE;
USE SCHEMA RAW;

CREATE FILE FORMAT IF NOT EXISTS parquet_format
    TYPE=PARQUET;

CREATE STAGE IF NOT EXISTS ercot_curated_stage
    URL='s3://ercot-grid-pipeline-curated/'
    STORAGE_INTEGRATION = ercot_s3_integration
    FILE_FORMAT=parquet_format;