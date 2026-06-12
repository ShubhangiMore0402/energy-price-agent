import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

def test_router():
    """Test LLM Router"""
    print("\n" + "="*60)
    print("TEST 1: LLM Router")
    print("="*60)
    
    from src.llm_router import create_router
    
    router = create_router()
    
    test_questions = [
        "What are the electricity prices today?",
        "When were prices high in January?",
        "Compare today with last week",
        "What was the cheapest hour in March 2026?",
    ]
    
    for question in test_questions:
        print(f"\nQuestion: {question}")
        result = router.detect_date_range(question)
        print(f"  Type: {result['query_type']}")
        print(f"  Start: {result.get('start_date', 'N/A')}")
        print(f"  End: {result.get('end_date', 'N/A')}")
        print(f"  Reasoning: {result['reasoning']}")


def test_mcp_server():
    """Test MCP Server"""
    print("\n" + "="*60)
    print("TEST 2: MCP Server")
    print("="*60)
    
    from src.mcp_server import get_mcp_server
    
    server = get_mcp_server()
    
    # Test query
    print("\nQuerying historical prices (Jan 2026)...")
    result = server.query_historical_prices("2026-01-12", "2026-01-12")
    
    if result["status"] == "success":
        print(f"✓ Retrieved {result['records']} records")
        print(f"  Avg Price: €{result['statistics']['avg_price']}/MWh")
        print(f"  Min Price: €{result['statistics']['min_price']}/MWh")
        print(f"  Max Price: €{result['statistics']['max_price']}/MWh")
    else:
        print(f"✗ Query failed: {result['message']}")


def test_formatter():
    """Test Response Formatter"""
    print("\n" + "="*60)
    print("TEST 3: Response Formatter")
    print("="*60)
    
    from src.llm_formatter import create_formatter
    
    formatter = create_formatter()
    
    # Mock analysis
    analysis = {
        "average_price": 95.50,
        "min_price": 70.00,
        "max_price": 145.00,
        "cheapest_hours": [
            {"hour": 2, "price_eur_mwh": 70.00},
            {"hour": 3, "price_eur_mwh": 75.50},
        ],
        "expensive_hours": [
            {"hour": 17, "price_eur_mwh": 145.00},
            {"hour": 16, "price_eur_mwh": 140.00},
        ],
        "estimated_saving_eur": 7.50,
        "example_kwh": 10
    }
    
    question = "When should I charge my EV today?"
    
    print(f"\nQuestion: {question}")
    response = formatter.format_response(
        user_question=question,
        data_source="today",
        analysis=analysis,
        use_case="EV charging"
    )
    
    print(f"Response:\n{response}")


def test_full_agent():
    """Test Full Agent with Routing"""
    print("\n" + "="*60)
    print("TEST 4: Full Agent with Routing")
    print("="*60)
    
    from src.agent import run_energy_agent
    
    test_cases = [
        {
            "question": "When is electricity cheapest today?",
            "use_case": "EV charging",
            "label": "Today Query"
        },
        {
            "question": "What were the prices like in January?",
            "use_case": "Dishwasher",
            "label": "Historical Query"
        },
    ]
    
    for test in test_cases:
        print(f"\n{test['label']}:")
        print(f"  Question: {test['question']}")
        print(f"  Use Case: {test['use_case']}")
        
        result = run_energy_agent(
            source="aWATTar",
            date="2026-06-11",
            question=test['question'],
            use_case=test['use_case']
        )
        
        print(f"  Data Source: {result.get('data_source', 'unknown')}")
        print(f"  Status: {'✓ Success' if not result['error'] else '✗ Error'}")
        print(f"  Response: {result['recommendation'][:100]}...")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("MCP INTEGRATION TEST SUITE")
    print("="*60)
    
    try:
        test_router()
    except Exception as e:
        print(f"\n✗ Router test failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_mcp_server()
    except Exception as e:
        print(f"\n✗ MCP Server test failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_formatter()
    except Exception as e:
        print(f"\n✗ Formatter test failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        test_full_agent()
    except Exception as e:
        print(f"\n✗ Full Agent test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETE")
    print("="*60)
