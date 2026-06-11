import sys
from pathlib import Path
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END

# Support both module imports and direct execution
try:
    from .tools import (
        fetch_price_tool,
        clean_data_tool,
        analyze_price_tool,
        recommendation_tool,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.tools import (
        fetch_price_tool,
        clean_data_tool,
        analyze_price_tool,
        recommendation_tool,
    )


class EnergyAgentState(TypedDict):
    source: str
    date: str
    question: str
    use_case: str
    raw_data: Any
    clean_data: Any
    analysis: dict
    recommendation: str
    api_status: str
    error: bool


def build_energy_agent():
    graph = StateGraph(EnergyAgentState)

    graph.add_node("fetch_prices", fetch_price_tool)
    graph.add_node("clean_data", clean_data_tool)
    graph.add_node("analyze_prices", analyze_price_tool)
    graph.add_node("recommend", recommendation_tool)

    graph.set_entry_point("fetch_prices")

    graph.add_edge("fetch_prices", "clean_data")
    graph.add_edge("clean_data", "analyze_prices")
    graph.add_edge("analyze_prices", "recommend")
    graph.add_edge("recommend", END)

    return graph.compile()


def run_energy_agent(source: str, date: str, question: str, use_case: str):
    app = build_energy_agent()

    initial_state = {
        "source": source,
        "date": date,
        "question": question,
        "use_case": use_case,
        "raw_data": None,
        "clean_data": None,
        "analysis": {},
        "recommendation": "",
        "api_status": "",
        "error": False
    }

    result = app.invoke(initial_state)
 
    return {
        "recommendation": result["recommendation"],
        "data": result["clean_data"],
        "analysis": result["analysis"],
        "api_status": result["api_status"],
        "error": result["error"],
    }