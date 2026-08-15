--this will show power grid operation with suffer or buffer 
--or approaching a grid outage

with demand_generation as (
    select
        period,
        respondent,
        report_date,
        demand_mwh,
        total_generation_mwh
    from {{ ref('mart_demand_vs_generation') }}
    group by period, respondent, report_date, demand_mwh, total_generation_mwh
),
interchange as (
    select 
        period,
        respondent,
        interchange_mwh,
        flow_direction
    from {{ ref('mart_interchange_balance') }}
),

joined as (
    select
       demand_generation.period,
       demand_generation.respondent,
       demand_generation.demand_mwh,
       demand_generation.total_generation_mwh,
       demand_generation.report_date,
       coalesce(interchange.interchange_mwh, 0) as interchange_mwh,
       coalesce(interchange.flow_direction,'no_data') as flow_direction,

       demand_generation.total_generation_mwh - coalesce(interchange.interchange_mwh, 0) as net_available_generation_mwh
    
    from demand_generation
    left join interchange
       on demand_generation.period = interchange.period
      and demand_generation.respondent = interchange.respondent
),

metrics as (
    select
       respondent,
       period,
       report_date,
       demand_mwh,
       total_generation_mwh,
       interchange_mwh,
       flow_direction,
       net_available_generation_mwh,
       (net_available_generation_mwh - demand_mwh)/ nullif(demand_mwh,0) as reserve_margin_pct
    
    from joined
),

final as (
    select
       period,
       respondent,
       report_date,
       demand_mwh,
       total_generation_mwh,
       interchange_mwh,
       flow_direction,
       net_available_generation_mwh,
       reserve_margin_pct,
       case
            when reserve_margin_pct is null then 'unknown'
            when reserve_margin_pct >=0.15 then 'surplus'
            when reserve_margin_pct >=0.05 then 'adequate'
            when reserve_margin_pct >=0.0 then 'tight'
            else 'deficit'
        end as grid_status
    from metrics

)

select * from final