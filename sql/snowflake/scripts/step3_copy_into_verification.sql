-- Manual verification of COPY INTO load mechanics — run directly in Snowsight
-- to prove the DELETE-then-COPY idempotency pattern before formalizing it
-- also for manula verification of the procedures testing the pattern


--RAW INTERCHANGE
USE DATABASE AWS_SNOWFLAKE_PIPELINE;
USE SCHEMA RAW;
SET run_date = '2026-08-11';

DELETE FROM raw_interchange WHERE dt = $run_date::DATE;
COPY INTO raw_interchange (respondent, period, value, value_units, ingestion_date, dt)
FROM (
    SELECT
        $1:respondent::VARCHAR,
        $1:period::TIMESTAMP_NTZ,
        $1:value::FLOAT,
        $1:value_units::VARCHAR,
        $1:ingestion_date::DATE,
        $run_date::DATE
    FROM @ercot_curated_stage/interchange/dt=2026-08-11/
)
FILE_FORMAT = (FORMAT_NAME = parquet_format)
PATTERN = '.*\\.parquet'
ON_ERROR = ABORT_STATEMENT;

--LIST @ercot_curated_stage/interchange/; test command

--RAW DEMAND
USE DATABASE AWS_SNOWFLAKE_PIPELINE;
USE SCHEMA RAW;
SET run_date='2026-08-10';
DELETE FROM raw_demand WHERE dt=$run_date::DATE;
COPY INTO raw_demand(respondent,period,value,value_units,ingestion_date,dt)
FROM(
      SELECT
      $1:respondent::VARCHAR,
      $1:period::TIMESTAMP_NTZ,
      $1:value::FLOAT,
      $1:value_units::VARCHAR,
      $1:ingestion_date::DATE,
      $run_date::DATE
    FROM @ercot_curated_stage/demand/dt=2026-08-10/
)
FILE_FORMAT=(FORMAT_NAME=parquet_format)
PATTERN = '.*\\.parquet'
ON_ERROR=ABORT_STATEMENT;

--LIST @ercot_curated_stage/demand/dt=2026-08-10/; test command

USE DATABASE AWS_SNOWFLAKE_PIPELINE;
USE SCHEMA RAW;
SET run_date = '2026-08-10';

DELETE FROM raw_generation_by_fuel WHERE dt = $run_date::DATE;

COPY INTO raw_generation_by_fuel (respondent, fuel_type, period, value, value_units, ingestion_date, dt)
FROM (
    SELECT
        $1:respondent::VARCHAR,
        $1:fuel_type::VARCHAR,
        $1:period::TIMESTAMP_NTZ,
        $1:value::FLOAT,
        $1:value_units::VARCHAR,
        $1:ingestion_date::DATE,
        $run_date::DATE
    FROM @ercot_curated_stage/generation_by_fuel/dt=2026-08-10/
)
FILE_FORMAT = (FORMAT_NAME = parquet_format)
PATTERN = '.*\\.parquet'
ON_ERROR = ABORT_STATEMENT;

--SELECT fuel_type, COUNT(*) FROM raw_generation_by_fuel
--WHERE dt = '2026-08-10'
--GROUP BY fuel_type
--ORDER BY fuel_type;