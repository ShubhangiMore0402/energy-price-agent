import sys
from pathlib import Path

# Support both module imports and direct execution
try:
    from .data_sources import fetch_awattar_prices
    from .preprocessing import clean_price_data
    from .analysis import analyze_prices, create_recommendation
    from .logger import logger
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.data_sources import fetch_awattar_prices
    from src.preprocessing import clean_price_data
    from src.analysis import analyze_prices, create_recommendation
    from src.logger import logger


def fetch_price_tool(state):
    source = state["source"]
    date = state["date"]

    logger.info(f"Starting price fetch | source={source} | date={date}")

    try:
        if source == "aWATTar":
            raw_df = fetch_awattar_prices(date)
        else:
            raise ValueError("Only aWATTar implemented as live API source.")

        state["raw_data"] = raw_df
        state["api_status"] = (
            f"{source} live API fetch successful for {date} | rows={len(raw_df)}"
        )
        state["error"] = False

        logger.info(f"Price fetch successful | rows={len(raw_df)}")

    except Exception as exc:
        logger.error(f"Price fetch failed | error={exc}")

        state["raw_data"] = None
        state["api_status"] = (
            f"No live price data available for {date}. Reason: {exc}"
        )
        state["error"] = True

    return state


def clean_data_tool(state):
    if state.get("error"):
        return state

    clean_df = clean_price_data(state["raw_data"])
    state["clean_data"] = clean_df
    return state


def analyze_price_tool(state):
    if state.get("error"):
        return state

    analysis = analyze_prices(state["clean_data"])
    state["analysis"] = analysis
    return state


def recommendation_tool(state):
    if state.get("error"):
        return state

    recommendation = create_recommendation(
        analysis=state["analysis"],
        question=state["question"],
        use_case=state["use_case"],
        date=state["date"]
    )

    state["recommendation"] = recommendation
    return state