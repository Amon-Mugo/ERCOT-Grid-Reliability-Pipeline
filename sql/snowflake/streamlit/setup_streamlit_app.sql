

-- sql/snowflake/streamlit/setup_streamlit_app.sql
-- Purpose: Creates a dedicated read-only role + XS warehouse for the
-- Streamlit-in-Snowflake dashboard, scoped to SELECT-only on the ANALYTICS
-- marts. Kept separate from ERCOT_ADMIN/ERCOT_TRANSFORMER so the app
-- can never write, matching the least-privilege pattern used elsewhere
-- in this project.

-- Step 1: account-level objects, requires ACCOUNTADMIN
USE ROLE ACCOUNTADMIN;

CREATE WAREHOUSE IF NOT EXISTS ercot_app_wh
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

CREATE ROLE IF NOT EXISTS ercot_app;
GRANT ROLE ercot_app TO USER AMON;
GRANT USAGE ON WAREHOUSE ercot_app_wh TO ROLE ercot_app;

-- Step 2: schema/db-level grants, ERCOT_ADMIN already owns these objects
USE ROLE ERCOT_ADMIN;

GRANT USAGE ON DATABASE aws_snowflake_pipeline TO ROLE ercot_app;
GRANT USAGE ON SCHEMA aws_snowflake_pipeline.analytics TO ROLE ercot_app;

GRANT SELECT ON TABLE aws_snowflake_pipeline.analytics.mart_grid_reliability TO ROLE ercot_app;
GRANT SELECT ON TABLE aws_snowflake_pipeline.analytics.mart_demand_vs_generation TO ROLE ercot_app;
GRANT SELECT ON TABLE aws_snowflake_pipeline.analytics.mart_interchange_balance TO ROLE ercot_app;

GRANT CREATE STREAMLIT ON SCHEMA aws_snowflake_pipeline.analytics TO ROLE ercot_app;
GRANT CREATE STAGE ON SCHEMA aws_snowflake_pipeline.analytics TO ROLE ercot_app;

GRANT ROLE ercot_app TO USER AMON;