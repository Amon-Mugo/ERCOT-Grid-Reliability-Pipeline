
-- ERCOT Grid Pipeline — Snowflake RAW schema DDL
-- Database: AWS_SNOWFLAKE_PIPELINE, Schema: RAW
-- Role: ERCOT_ADMIN / WAREHOUSE_CONNECT

USE DATABASE AWS_SNOWFLAKE_PIPELINE;
USE SCHEMA RAW;

CREATE TABLE IF NOT EXISTS raw_demand (
    respondent      VARCHAR       NOT NULL,
    period          TIMESTAMP_NTZ NOT NULL,
    value           FLOAT,
    value_units     VARCHAR,
    ingestion_date  DATE          NOT NULL,
    dt              DATE          NOT NULL, -- S3 partition date
    CONSTRAINT pk_raw_demand PRIMARY KEY (respondent, period) RELY DISABLE
);

CREATE TABLE IF NOT EXISTS raw_interchange (
    respondent      VARCHAR       NOT NULL,
    period          TIMESTAMP_NTZ NOT NULL,
    value           FLOAT,
    value_units     VARCHAR,
    ingestion_date  DATE          NOT NULL,
    dt              DATE          NOT NULL,
    CONSTRAINT pk_raw_interchange PRIMARY KEY (respondent, period) RELY DISABLE
);

CREATE TABLE IF NOT EXISTS raw_generation_by_fuel (
    respondent      VARCHAR       NOT NULL,
    fuel_type       VARCHAR       NOT NULL,
    period          TIMESTAMP_NTZ NOT NULL,
    value           FLOAT,
    value_units     VARCHAR,
    ingestion_date  DATE          NOT NULL,
    dt              DATE          NOT NULL,
    CONSTRAINT pk_raw_generation PRIMARY KEY (respondent, fuel_type, period) RELY DISABLE
);
