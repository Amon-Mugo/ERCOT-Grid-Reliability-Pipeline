with base as (
    select
        respondent,
        period,
        value as demand_mwh,
        value_units as demand_units,
        dt as report_date

    from {{ source('ercot_raw','raw_demand') }}
)

select * from base
