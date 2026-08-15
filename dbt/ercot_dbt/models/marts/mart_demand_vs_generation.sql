with generation as (
    select * from {{ ref('stg_generation_by_fuel') }}

),
demand as(
    select * from {{ ref('stg_demand') }}
),

joined as (
    select
        generation.respondent,
        generation.period,
        generation.fuel_type,
        generation.report_date,
        generation.generation_mwh,
        generation.generation_units,
        demand.demand_mwh,
        demand.demand_units
    from generation
    left join demand
      on generation.period = demand.period
      and generation.respondent = demand.respondent
),

--window functions

final as (
    select
        respondent,
        period,
        fuel_type,
        report_date,
        generation_mwh,
        generation_units,
        demand_mwh,
        demand_units,

        sum(generation_mwh) over (partition by period) as total_generation_mwh,
        sum(generation_mwh) over (partition by period) - demand_mwh as supply_demand_delta_mwh
    
    from joined 
)

select * from final