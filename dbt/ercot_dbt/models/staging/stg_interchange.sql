with base as (
    SELECT
        respondent,
        period,
        value    as interchange_mwh,
        value_units as interchange_units,
        dt    as report_date
    from {{source('ercot_raw','raw_interchange')}}
)
select * from base 