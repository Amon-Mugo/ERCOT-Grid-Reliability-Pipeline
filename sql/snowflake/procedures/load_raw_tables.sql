-- Reusable load procedures for the RAW layer — one per table.

USE DATABASE AWS_SNOWFLAKE_PIPELINE;
USE SCHEMA RAW;

-- 1. LOAD RAW DEMAND
-- 2. LOAD RAW INTERCHANGE
-- 3. LOAD RAW GENERATION BY FUEL

CREATE OR REPLACE PROCEDURE load_raw_generation_by_fuel(run_date DATE)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
    v_run_date STRING;
    v_sql       STRING;
    null_run_date_exception EXCEPTION (-20001, 'run_date parameter cannot be NULL.');
BEGIN
    IF (run_date IS NULL) THEN
        RAISE null_run_date_exception;
    END IF;

    v_run_date := TO_VARCHAR(:run_date, 'YYYY-MM-DD');

    BEGIN TRANSACTION;

    DELETE FROM raw_generation_by_fuel WHERE dt = :run_date;

    v_sql := 'COPY INTO raw_generation_by_fuel (respondent, fuel_type, period, value, value_units, ingestion_date, dt) ' ||
             'FROM (SELECT ' ||
             '  $1:respondent::VARCHAR, ' ||
             '  $1:fuel_type::VARCHAR, ' ||
             '  $1:period::TIMESTAMP_NTZ, ' ||
             '  $1:value::FLOAT, ' ||
             '  $1:value_units::VARCHAR, ' ||
             '  $1:ingestion_date::DATE, ' ||
             '  ''' || v_run_date || '''::DATE ' ||
             'FROM @ercot_curated_stage/generation_by_fuel/dt=' || v_run_date || '/) ' ||
             'FILE_FORMAT = (FORMAT_NAME = parquet_format) ' ||
             'PATTERN = ''.*\\.parquet'' ' ||
             'ON_ERROR = ABORT_STATEMENT ' ||
             'FORCE = TRUE';

    EXECUTE IMMEDIATE :v_sql;

    COMMIT;

    RETURN 'raw_generation_by_fuel loaded for dt=' || v_run_date;
END;
$$;


CREATE OR REPLACE PROCEDURE load_raw_demand(run_date DATE)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
    v_run_date STRING;
    v_sql       STRING;
    null_run_date_exception EXCEPTION (-20001, 'run_date parameter cannot be NULL.');
BEGIN
    IF (run_date IS NULL) THEN
        RAISE null_run_date_exception;
    END IF;
    v_run_date := TO_VARCHAR(:run_date, 'YYYY-MM-DD');

    BEGIN TRANSACTION;

    DELETE FROM raw_demand WHERE dt = :run_date;
    v_sql := 'COPY INTO raw_demand (respondent, period, value, value_units, ingestion_date, dt) ' ||
             'FROM (SELECT ' ||
             '  $1:respondent::VARCHAR, ' ||
             '  $1:period::TIMESTAMP_NTZ, ' ||
             '  $1:value::FLOAT, ' ||
             '  $1:value_units::VARCHAR, ' ||
             '  $1:ingestion_date::DATE, ' ||
             '  ''' || v_run_date || '''::DATE ' ||
             'FROM @ercot_curated_stage/demand/dt=' || v_run_date || '/) ' ||
             'FILE_FORMAT = (FORMAT_NAME = parquet_format) ' ||
             'PATTERN = ''.*\\.parquet'' ' ||
             'ON_ERROR = ABORT_STATEMENT ' ||
             'FORCE = TRUE';
    EXECUTE IMMEDIATE :v_sql;

    COMMIT;

    RETURN 'raw_demand loaded for dt=' || v_run_date;
END;
$$;


CREATE OR REPLACE PROCEDURE load_raw_interchange(run_date DATE)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
    v_run_date STRING;
    v_sql       STRING;
    null_run_date_exception EXCEPTION (-20001, 'run_date parameter cannot be NULL.');
BEGIN
    IF (run_date IS NULL) THEN
        RAISE null_run_date_exception;
    END IF;

    v_run_date := TO_VARCHAR(:run_date, 'YYYY-MM-DD');

    BEGIN TRANSACTION;

    DELETE FROM raw_interchange WHERE dt = :run_date;

    v_sql := 'COPY INTO raw_interchange (respondent, period, value, value_units, ingestion_date, dt) ' ||
             'FROM (SELECT ' ||
             '  $1:respondent::VARCHAR, ' ||
             '  $1:period::TIMESTAMP_NTZ, ' ||
             '  $1:value::FLOAT, ' ||
             '  $1:value_units::VARCHAR, ' ||
             '  $1:ingestion_date::DATE, ' ||
             '  ''' || v_run_date || '''::DATE ' ||
             'FROM @ercot_curated_stage/interchange/dt=' || v_run_date || '/) ' ||
             'FILE_FORMAT = (FORMAT_NAME = parquet_format) ' ||
             'PATTERN = ''.*\\.parquet'' ' ||
             'ON_ERROR = ABORT_STATEMENT ' ||
             'FORCE = TRUE';

    EXECUTE IMMEDIATE :v_sql;

    COMMIT;

    RETURN 'raw_interchange loaded for dt=' || v_run_date;
END;
$$;


--CALL load_raw_demand('2026-08-10');
--SELECT COUNT(*) FROM raw_demand WHERE dt = '2026-08-10';  -- expect 24

--CALL load_raw_interchange('2026-08-11');
--SELECT COUNT(*) FROM raw_interchange WHERE dt = '2026-08-11';  -- expect 5

--ALL load_raw_generation_by_fuel('2026-08-10');
--ELECT COUNT(*) FROM raw_generation_by_fuel WHERE dt = '2026-08-10';  -- expect 192