import streamlit as st
import plotly.express as px
from datetime import date

from src.agent import run_energy_agent

st.set_page_config(
    page_title="Energy Price Intelligence Agent",
    layout="wide"
)

st.title("⚡ Energy Price Intelligence Agent")
st.write("Find the best time to use electricity based on live energy price data.")

# Sidebar
with st.sidebar.expander("ℹ️ About This Project"):
    st.markdown(
        """
        **Energy Price Intelligence Agent**

        This AI-powered application analyzes live electricity market prices and helps identify the most cost-effective time windows for energy consumption.

        **Built using:**
        - LangGraph
        - Python
        - Streamlit
        - Plotly
        - Live Energy APIs
        """
    )

source = st.sidebar.selectbox("Data source", ["aWATTar"])

selected_date = st.sidebar.date_input(
    "Select date",
    value=date.today()
)

use_case = st.sidebar.selectbox(
    "Use case",
    [
        "EV charging",
        "Washing machine",
        "Dishwasher",
        "Battery charging",
        "Heat pump"
    ]
)

question = st.sidebar.text_area(
    "Ask your question",
    "When is electricity cheapest today?"
)

show_details = st.sidebar.checkbox(
    "Show Technical Details",
    value=False
)

run_button = st.sidebar.button("Run Analysis")

if run_button:
    result = run_energy_agent(
        source=source,
        date=str(selected_date),
        question=question,
        use_case=use_case
    )

    if result.get("error"):
        st.error(result["api_status"])
        st.stop()

    df = result["data"]
    analysis = result["analysis"]

    # Recommendation
    st.subheader("Recommendation")
    st.info(result["recommendation"])

    # KPI Cards
    st.subheader("Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Average Price", f"{analysis['average_price']} €/MWh")
    col2.metric("Cheapest Price", f"{analysis['min_price']} €/MWh")
    col3.metric("Highest Price", f"{analysis['max_price']} €/MWh")
    col4.metric(
        "Estimated Saving",
        f"€{analysis['estimated_saving_eur']}",
        help=f"Estimated saving by shifting {analysis['example_kwh']} kWh from highest-price hour to cheapest-price hour."
    )

    # Chart
    st.subheader("Price Trend Chart")

    fig = px.line(
        df,
        x="hour",
        y="price_eur_mwh",
        markers=True,
        title="Hourly Electricity Price",
        labels={
            "hour": "Hour of Day",
            "price_eur_mwh": "Price (€/MWh)"
        }
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tables
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Cheapest Hours")
        st.dataframe(analysis["cheapest_hours"], use_container_width=True)

    with col_right:
        st.subheader("Most Expensive Hours")
        st.dataframe(analysis["expensive_hours"], use_container_width=True)

    # Optional technical details
    if show_details:
        st.subheader("Technical Details")
        st.json({
            "source": source,
            "selected_date": str(selected_date),
            "use_case": use_case,
            "question": question,
            "rows_fetched": len(df),
            "api_status": result["api_status"]
        })

else:
    st.info("Choose your settings from the sidebar and click **Run Analysis**.")