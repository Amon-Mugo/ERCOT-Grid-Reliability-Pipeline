with base as (
    select
        respondent,
        fuel_type,
        period,
        value as generation_mwh,
        value_units as generation_units,
        dt as report_date

    from {{ source('ercot_raw','raw_generation_by_fuel') }}
)

select * from base
