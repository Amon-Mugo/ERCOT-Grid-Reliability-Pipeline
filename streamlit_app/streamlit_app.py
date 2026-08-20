# streamlit_app/streamlit_app.py
# Purpose: Streamlit-in-Snowflake dashboard reading directly from the three
# dbt marts (grid_reliability, demand_vs_generation, interchange_balance).
# Runs inside Snowflake using the native Snowpark session — no external
# credentials or hosting required.

import altair as alt
import pandas as pd
import streamlit as st
from snowflake.snowpark.context import get_active_session

session = get_active_session()

st.set_page_config(page_title="ERCOT Grid Reliability", layout="wide")
st.title("ERCOT Grid Reliability Dashboard")

MART_SCHEMA = "aws_snowflake_pipeline.analytics"


@st.cache_data(ttl=600)
def load_mart(table_name: str) -> pd.DataFrame:
    """Pull a mart table into a pandas DataFrame, cached for 10 minutes
    so repeated tab switches don't re-hit the warehouse."""
    return session.table(f"{MART_SCHEMA}.{table_name}").to_pandas()


reliability_df = load_mart("mart_grid_reliability")
demand_gen_df = load_mart("mart_demand_vs_generation")
interchange_df = load_mart("mart_interchange_balance")

tab_reliability, tab_demand_gen, tab_interchange = st.tabs(
    ["Grid Reliability", "Demand vs Generation", "Interchange Balance"]
)

# ---------------------------------------------------------------------------
# Tab 1: Grid Reliability (mart_grid_reliability)
# columns: PERIOD, RESPONDENT, REPORT_DATE, DEMAND_MWH, TOTAL_GENERATION_MWH,
#          INTERCHANGE_MWH, FLOW_DIRECTION, NET_AVAILABLE_GENERATION_MWH,
#          RESERVE_MARGIN_PCT (decimal fraction), GRID_STATUS
# ---------------------------------------------------------------------------
with tab_reliability:
    latest = reliability_df.sort_values("PERIOD").iloc[-1]

    col1, col2, col3 = st.columns(3)
    col1.metric("Reserve Margin", f"{latest['RESERVE_MARGIN_PCT'] * 100:.1f}%")
    col2.metric("Grid Status", str(latest["GRID_STATUS"]).capitalize())
    col3.metric(
        "Net Available Generation (MWh)",
        f"{latest['NET_AVAILABLE_GENERATION_MWH']:,.0f}",
    )

    st.subheader("Reserve Margin Over Time")
    plot_df = reliability_df.copy()
    plot_df["RESERVE_MARGIN_PCT_DISPLAY"] = plot_df["RESERVE_MARGIN_PCT"] * 100

    margin_chart = (
        alt.Chart(plot_df)
        .mark_line()
        .encode(
            x="PERIOD:T",
            y=alt.Y("RESERVE_MARGIN_PCT_DISPLAY:Q", title="Reserve Margin (%)"),
            color=alt.value("#1f77b4"),
        )
        .properties(height=350)
    )
    # NERC target reference line at ~13.75%, matching the mart's status buckets
    target_line = (
        alt.Chart(pd.DataFrame({"y": [13.75]}))
        .mark_rule(strokeDash=[4, 4], color="red")
        .encode(y="y:Q")
    )
    st.altair_chart(margin_chart + target_line, use_container_width=True)

    st.subheader("Grid Status Distribution")
    # Order matches the case statement: surplus > adequate > tight > deficit > unknown
    status_order = ["surplus", "adequate", "tight", "deficit", "unknown"]
    status_counts = (
        reliability_df["GRID_STATUS"]
        .value_counts()
        .reindex(status_order)
        .fillna(0)
        .reset_index()
    )
    status_counts.columns = ["status", "count"]
    st.bar_chart(status_counts.set_index("status"))

# ---------------------------------------------------------------------------
# Tab 2: Demand vs Generation (mart_demand_vs_generation)
# columns: RESPONDENT, PERIOD, FUEL_TYPE, REPORT_DATE, GENERATION_MWH,
#          GENERATION_UNITS, DEMAND_MWH, DEMAND_UNITS, TOTAL_GENERATION_MWH,
#          SUPPLY_DEMAND_DELTA_MWH
# ---------------------------------------------------------------------------
with tab_demand_gen:
    st.subheader("Generation by Fuel Type vs Demand")

    gen_area = (
        alt.Chart(demand_gen_df)
        .mark_area()
        .encode(
            x="PERIOD:T",
            y=alt.Y("GENERATION_MWH:Q", stack="zero", title="Generation (MWh)"),
            color=alt.Color("FUEL_TYPE:N", title="Fuel Type"),
        )
        .properties(height=400)
    )

    # DEMAND_MWH repeats per fuel_type row for a given period, so dedupe on period
    demand_line_df = demand_gen_df.drop_duplicates(subset="PERIOD")[
        ["PERIOD", "DEMAND_MWH"]
    ]
    demand_line = (
        alt.Chart(demand_line_df)
        .mark_line(color="black", strokeWidth=2)
        .encode(x="PERIOD:T", y="DEMAND_MWH:Q")
    )

    st.altair_chart(gen_area + demand_line, use_container_width=True)
    st.caption("Black line = total demand. Stacked areas = generation by fuel type.")

    st.subheader("Supply-Demand Delta Over Time")
    delta_df = demand_gen_df.drop_duplicates(subset="PERIOD")[
        ["PERIOD", "SUPPLY_DEMAND_DELTA_MWH"]
    ]
    delta_chart = (
        alt.Chart(delta_df)
        .mark_bar()
        .encode(
            x="PERIOD:T",
            y=alt.Y("SUPPLY_DEMAND_DELTA_MWH:Q", title="Supply - Demand (MWh)"),
            color=alt.condition(
                "datum.SUPPLY_DEMAND_DELTA_MWH >= 0",
                alt.value("#2ca02c"),
                alt.value("#d62728"),
            ),
        )
        .properties(height=250)
    )
    st.altair_chart(delta_chart, use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 3: Interchange Balance (mart_interchange_balance)
# columns: PERIOD, RESPONDENT, INTERCHANGE_MWH, INTERCHANGE_UNITS,
#          FLOW_DIRECTION ('net_export' | 'net_import' | 'balanced' | null)
# ---------------------------------------------------------------------------
with tab_interchange:
    units = interchange_df["INTERCHANGE_UNITS"].dropna().iloc[0] if not interchange_df["INTERCHANGE_UNITS"].dropna().empty else "MWh"
    st.subheader(f"Net Interchange Over Time ({units})")

    flow_color_scale = alt.Scale(
        domain=["net_export", "net_import", "balanced"],
        range=["#2ca02c", "#d62728", "#7f7f7f"],
    )

    interchange_chart = (
        alt.Chart(interchange_df)
        .mark_bar()
        .encode(
            x="PERIOD:T",
            y=alt.Y("INTERCHANGE_MWH:Q", title=f"Interchange ({units})"),
            color=alt.Color(
                "FLOW_DIRECTION:N", title="Flow Direction", scale=flow_color_scale
            ),
        )
        .properties(height=350)
    )
    st.altair_chart(interchange_chart, use_container_width=True)

    st.subheader("Flow Direction Breakdown")
    flow_order = ["net_export", "net_import", "balanced"]
    flow_counts = (
        interchange_df["FLOW_DIRECTION"]
        .value_counts()
        .reindex(flow_order)
        .fillna(0)
        .reset_index()
    )
    flow_counts.columns = ["flow_direction", "count"]
    st.bar_chart(flow_counts.set_index("flow_direction"))