import streamlit as st
import plotly.express as px
import inspect
from datetime import date

from src.agent import run_energy_agent


def detect_use_cases_from_prompt(prompt: str, default_use_case: str) -> str:
    prompt_lower = prompt.lower()
    detected = []

    if "ev" in prompt_lower or "car" in prompt_lower or "charge" in prompt_lower:
        detected.append("EV charging")

    if "dishwasher" in prompt_lower:
        detected.append("Dishwasher")

    if "washing" in prompt_lower or "laundry" in prompt_lower:
        detected.append("Washing machine")

    if "battery" in prompt_lower or "storage" in prompt_lower:
        detected.append("Battery charging")

    if "heat pump" in prompt_lower or "heating" in prompt_lower:
        detected.append("Heat pump")

    if detected:
        return ", ".join(detected)

    return default_use_case


def run_agent_compat(source: str, selected_date, question: str, use_case: str):
    """
    Call run_energy_agent with or without selected_date depending on the imported signature.
    This keeps the app working if Streamlit is still holding an older module version.
    """
    agent_params = inspect.signature(run_energy_agent).parameters

    if "selected_date" in agent_params:
        return run_energy_agent(
            source=source,
            date=str(selected_date),
            selected_date=str(selected_date),
            question=question,
            use_case=use_case,
        )

    return run_energy_agent(
        source=source,
        date=str(selected_date),
        question=question,
        use_case=use_case,
    )


st.set_page_config(
    page_title="Energy Price Intelligence Agent",
    layout="wide"
)

# CSS to make right chat panel feel like sidebar
st.markdown(
    """
    <style>
    .right-chat-panel {
        border-left: 1px solid rgba(128, 128, 128, 0.25);
        padding-left: 1rem;
        min-height: 85vh;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("⚡ Energy Price Intelligence Agent")
st.write("Find the best time to use electricity based on live energy price data.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Left sidebar
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

st.sidebar.caption(f"Analysis date in use: {selected_date}")

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
    "When is electricity cheapest?"
)

show_details = st.sidebar.checkbox(
    "Show Technical Details",
    value=False
)

run_button = st.sidebar.button("Run Analysis")

# Main page split: dashboard + right collapsible chatbot panel
dashboard_col, chat_col = st.columns([4.2, 1.25], gap="large")

with dashboard_col:
    if run_button:
        st.info(f"Analyzing data for: {selected_date}")

        result = run_agent_compat(
            source=source,
            selected_date=selected_date,
            question=question,
            use_case=use_case,
        )

        if result.get("error"):
            st.error(result["api_status"])
            st.stop()

        df = result["data"]
        analysis = result["analysis"]
        data_source = result.get("data_source", "unknown")

        st.subheader("Recommendation")
        st.info(result["recommendation"])

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

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Cheapest Hours")
            st.dataframe(analysis["cheapest_hours"], use_container_width=True)

        with col_right:
            st.subheader("Most Expensive Hours")
            st.dataframe(analysis["expensive_hours"], use_container_width=True)

        if show_details:
            st.subheader("Technical Details")
            st.json({
                "source": source,
                "selected_date": str(selected_date),
                "use_case": use_case,
                "question": question,
                "data_source": data_source,
                "rows_fetched": len(df),
                "api_status": result["api_status"]
            })

    else:
        st.info("Choose your settings from the sidebar and click **Run Analysis**.")

with chat_col:
    #st.markdown('<div class="right-chat-panel">', unsafe_allow_html=True)

    st.markdown("### 💬 Energy Assistant")

    with st.expander("Open Chatbot", expanded=False):
        st.caption("Ask about EV charging, dishwasher, battery, heat pump, or savings.")
        st.caption(f"Chat is analyzing: {selected_date}")

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        user_prompt = st.chat_input("Ask about prices...")

        if user_prompt:
            st.session_state.messages.append({
                "role": "user",
                "content": user_prompt
            })

            detected_use_cases = detect_use_cases_from_prompt(
                user_prompt,
                default_use_case=use_case
            )

            chat_result = run_agent_compat(
                source=source,
                selected_date=selected_date,
                question=user_prompt,
                use_case=detected_use_cases,
            )

            if chat_result.get("error"):
                assistant_response = chat_result["api_status"]
            else:
                assistant_response = chat_result["recommendation"]

            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_response
            })

            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)