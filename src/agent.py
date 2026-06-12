import sys
from pathlib import Path
from typing import TypedDict, Any
import pandas as pd
from langgraph.graph import StateGraph, END
import json

# Support both module imports and direct execution
try:
    from .tools import (fetch_price_tool, clean_data_tool,
        analyze_price_tool,recommendation_tool)
    from .data_sources import backfill_price_day_to_db
    from .llm_router import create_router
    from .llm_formatter import create_formatter
    from .mcp_server import get_mcp_server
    from .logger import logger
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.tools import (fetch_price_tool, clean_data_tool, 
                           analyze_price_tool, recommendation_tool)
    from src.data_sources import backfill_price_day_to_db
    from src.llm_router import create_router
    from src.llm_formatter import create_formatter
    from src.mcp_server import get_mcp_server
    from src.logger import logger


class EnergyAgentState(TypedDict):
    source: str
    date: str
    selected_date: str
    question: str
    use_case: str
    raw_data: Any
    clean_data: Any
    analysis: dict
    recommendation: str
    api_status: str
    error: bool
    data_source_type: str  # "today" | "historical" | "both"
    router_info: dict  # Route detection result


def route_query_node(state):
    """
    LLM Router node: Detects if query is about today or historical data
    """
    try:
        logger.info(
            f"CHATBOT QUESTION | question={state['question']} | selected_date={state.get('selected_date')} | use_case={state.get('use_case')}"
        )
        logger.info(
            f"ROUTER START | question={state['question']} | selected_date={state.get('selected_date')}"
        )
        router = create_router()
        route_info = router.detect_date_range(
            state["question"],
            selected_date=state.get("selected_date")
        )
        
        logger.info(f"Query routed to: {route_info['query_type']}")
        logger.info(
            f"ROUTER RESULT | query_type={route_info.get('query_type')} | start_date={route_info.get('start_date')} | end_date={route_info.get('end_date')} | reasoning={route_info.get('reasoning')}"
        )
        
        state["data_source_type"] = route_info["query_type"]
        state["router_info"] = route_info
        state["error"] = False
        
    except Exception as e:
        logger.error(f"Routing error: {e}")
        state["data_source_type"] = "today"  # Default fallback
        state["router_info"] = {
            "query_type": "today",
            "start_date": None,
            "end_date": None,
            "error": str(e)
        }
        state["error"] = False  # Don't fail, just use default
    
    return state


def fetch_prices_with_routing(state):
    """
    Enhanced fetch that uses either live API or MCP based on routing
    """
    route_info = state.get("router_info", {})
    query_type = state.get("data_source_type", "today")

    def _query_historical_with_backfill(start_date: str, end_date: str, hour=None):
        server = get_mcp_server()
        logger.info(
            f"MCP CALL | query_historical_prices | start_date={start_date} | end_date={end_date} | hour={hour}"
        )
        result = server.query_historical_prices(start_date, end_date, hour)

        if result["status"] != "no_data":
            logger.info(
                f"MCP CALL RESULT | status={result['status']} | start_date={start_date} | end_date={end_date} | hour={hour}"
            )
            return result

        # If the exact day is missing, fetch it on demand and retry once.
        if start_date == end_date:
            logger.info(f"Historical day missing in DB, backfilling {start_date}")
            backfill_price_day_to_db(start_date)
            logger.info(f"MCP CALL | retry historical_prices after backfill | date={start_date}")
            return server.query_historical_prices(start_date, end_date, hour)

        return result
    
    try:
        if query_type == "today":
            # Use live API
            logger.info("Fetching live price data from aWATTar API")
            state = fetch_price_tool(state)
            state["api_status"] = f"Live API: {state['api_status']}"
        
        elif query_type == "historical":
            # Use MCP to query historical data
            logger.info("Fetching historical data from PostgreSQL via MCP")
            logger.info(
                f"HISTORICAL ROUTE | start_date={route_info.get('start_date')} | end_date={route_info.get('end_date')} | selected_date={state.get('selected_date')}"
            )
            mcp_params = {
                "start_date": route_info.get("start_date", state["date"]),
                "end_date": route_info.get("end_date", state["date"]),
            }
            
            result = _query_historical_with_backfill(
                mcp_params["start_date"],
                mcp_params["end_date"],
                route_info.get("specific_hour")
            )
            
            if result["status"] == "success":
                # Convert to DataFrame format compatible with rest of pipeline
                df = pd.DataFrame(result["data"])
                state["raw_data"] = df
                state["api_status"] = f"Historical DB: Retrieved {result['records']} records from {mcp_params['start_date']} to {mcp_params['end_date']}"
                state["error"] = False
            else:
                state["raw_data"] = None
                state["api_status"] = f"Historical DB Error: {result['message']}"
                state["error"] = True
        
        elif query_type == "both":
            # Fetch both live and historical
            logger.info("Fetching both live and historical data")
            
            # Get live data
            state = fetch_price_tool(state)
            live_data = state["raw_data"]
            
            # Get historical data
            mcp_params = {
                "start_date": route_info.get("start_date"),
                "end_date": route_info.get("end_date"),
            }
            
            hist_result = _query_historical_with_backfill(
                mcp_params["start_date"],
                mcp_params["end_date"]
            )
            
            if hist_result["status"] == "success":
                hist_data = pd.DataFrame(hist_result["data"])
                # Combine: live + historical
                state["raw_data"] = pd.concat([hist_data, live_data], ignore_index=True)
                state["api_status"] = f"Combined: {len(live_data)} live records + {len(hist_data)} historical records"
                state["error"] = False
            else:
                state["api_status"] = f"Live data OK, historical failed: {hist_result['message']}"
    
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        state["raw_data"] = None
        state["api_status"] = f"Fetch failed: {str(e)}"
        state["error"] = True
    
    return state


def format_response_node(state):
    """
    LLM Formatter node: Converts analysis into natural language response
    """
    try:
        formatter = create_formatter()
        logger.info(
            f"FORMAT START | data_source={state.get('data_source_type')} | question={state.get('question')}"
        )
        
        formatted_response = formatter.format_response(
            user_question=state["question"],
            data_source=state["data_source_type"],
            analysis=state["analysis"],
            use_case=state["use_case"],
            raw_data=state["clean_data"]
        )

        route_info = state.get("router_info", {})
        start_date = route_info.get("start_date")
        end_date = route_info.get("end_date") or start_date or state.get("selected_date")

        if state.get("data_source_type") == "historical" and start_date:
            if end_date and end_date != start_date:
                formatted_response = f"Range analyzed: {start_date} to {end_date}. {formatted_response}"
            else:
                formatted_response = f"Date analyzed: {start_date}. {formatted_response}"

        logger.info(
            f"FORMAT RESULT | data_source={state.get('data_source_type')} | response_preview={formatted_response[:140]}"
        )
        
        state["recommendation"] = formatted_response
        logger.info("Response formatted successfully")
        
    except Exception as e:
        logger.error(f"Formatting error: {e}")
        # Fall back to old recommendation
        state["recommendation"] = state.get("recommendation", "Unable to generate recommendation")
    
    return state


def build_energy_agent():
    """Build enhanced LangGraph agent with routing and formatting"""
    graph = StateGraph(EnergyAgentState)

    # Add nodes
    graph.add_node("route_query", route_query_node)
    graph.add_node("fetch_prices", fetch_prices_with_routing)
    graph.add_node("clean_data", clean_data_tool)
    graph.add_node("analyze_prices", analyze_price_tool)
    graph.add_node("recommend", recommendation_tool)
    graph.add_node("format_response", format_response_node)

    # Set entry point
    graph.set_entry_point("route_query")

    # Add edges
    graph.add_edge("route_query", "fetch_prices")
    graph.add_edge("fetch_prices", "clean_data")
    graph.add_edge("clean_data", "analyze_prices")
    graph.add_edge("analyze_prices", "recommend")
    graph.add_edge("recommend", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()


def run_energy_agent(source: str, date: str, question: str, use_case: str, selected_date: str = None):
    """
    Run the enhanced energy agent with routing and formatting
    """
    app = build_energy_agent()

    initial_state = {
        "source": source,
        "date": date,
        "selected_date": selected_date or date,
        "question": question,
        "use_case": use_case,
        "raw_data": None,
        "clean_data": None,
        "analysis": {},
        "recommendation": "",
        "api_status": "",
        "error": False,
        "data_source_type": "today",
        "router_info": {}
    }

    result = app.invoke(initial_state)
 
    return {
        "recommendation": result["recommendation"],
        "data": result["clean_data"],
        "analysis": result["analysis"],
        "api_status": result["api_status"],
        "error": result["error"],
        "data_source": result.get("data_source_type", "unknown"),
    }