with interchange as (
    select * from {{ ref('stg_interchange') }}
),

final as (
    select
        period,
        respondent,
        interchange_mwh,
        interchange_units,
        case
            when interchange_mwh > 0 then 'net_export'
            when interchange_mwh < 0 then 'net_import'
            when interchange_mwh = 0 then 'balanced'
        end as flow_direction
    from interchange
)

select * from final
