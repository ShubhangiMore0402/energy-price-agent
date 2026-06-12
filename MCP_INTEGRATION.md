# MCP Integration for Energy Price Agent

## Overview

This document explains the Model Context Protocol (MCP) integration added to the Energy Price Intelligence Agent. This implementation demonstrates a production-grade pattern for intelligent routing between live APIs and historical databases.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Question                         │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  LLM Router                 │
        │  (Query Classification)     │
        │  ├─ Detect: Today/Hist      │
        │  ├─ Extract Dates           │
        │  ├─ Extract Hour Filters    │
        │  └─ Fallback Regex Patterns │
        └──────────────┬──────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
   ┌────▼─────┐              ┌───────▼────┐
   │  Today?  │              │ Historical?│
   └────┬─────┘              └───────┬────┘
        │                            │
   ┌────▼────────────┐    ┌─────────▼──────────┐
   │  aWATTar API    │    │  MCP Server        │
   │  (Live Data)    │    │  ├─ PostgreSQL     │
   │                 │    │  ├─ Query Tools    │
   │  Fetch today's  │    │  ├─ Stats Tools    │
   │  24 hour prices │    │  └─ Analysis Tools │
   └────┬────────────┘    └─────────┬──────────┘
        │                            │
        └────────────┬───────────────┘
                     │
        ┌────────────▼───────────────┐
        │  Analysis Pipeline         │
        │  ├─ Clean Data             │
        │  ├─ Calculate Stats        │
        │  └─ Identify Patterns      │
        └────────────┬───────────────┘
                     │
        ┌────────────▼──────────────┐
        │  LLM Formatter            │
        │  (Response Generation)    │
        │  ├─ Contextual Answer     │
        │  ├─ Actionable Tips       │
        │  ├─ Fallback Format       │
        │  └─ Natural Language      │
        └────────────┬──────────────┘
                     │
        ┌────────────▼──────────────┐
        │    User Response          │
        │  (Formatted & Friendly)   │
        └───────────────────────────┘
```

## Components

### 1. **LLM Router** (`src/llm_router.py`)

**Purpose:** Intelligently classify queries to route them to appropriate data source.

**Features:**
- Uses LLM (GPT-4o-mini) to understand natural language
- Detects if asking about: today, historical, or both
- Extracts date ranges and specific hours
- **Fallback mechanism:** Regex patterns for keyword matching when LLM unavailable

**Example Usage:**
```python
from src.llm_router import create_router

router = create_router()
route = router.detect_date_range("When were prices high in January?")
# Returns: {
#   "query_type": "historical",
#   "start_date": "2026-01-01",
#   "end_date": "2026-01-28",
#   "specific_hour": None,
#   "reasoning": "Detected January"
# }
```

### 2. **MCP Server** (`src/mcp_server.py`)

**Purpose:** Exposes historical price data as MCP tools for the agent to query.

**Tools Exposed:**
- `query_historical_prices(start_date, end_date, hour)` - Get price data for date range
- `get_price_statistics(start_date, end_date)` - Get aggregated statistics
- `find_cheapest_hours(start_date, end_date, top_n)` - Find cheapest time slots

**Example Usage:**
```python
from src.mcp_server import get_mcp_server

server = get_mcp_server()
result = server.query_historical_prices("2026-01-12", "2026-01-12")
# Returns: {
#   "status": "success",
#   "records": 24,
#   "statistics": {
#     "avg_price": 104.48,
#     "min_price": 76.59,
#     "max_price": 132.76
#   },
#   "data": [...]
# }
```

**Database Schema:**
```sql
CREATE TABLE electricity_prices (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP UNIQUE NOT NULL,
    hour INT NOT NULL,
    price_eur_mwh FLOAT NOT NULL,
    source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. **LLM Formatter** (`src/llm_formatter.py`)

**Purpose:** Formats analysis results into natural, conversational responses.

**Features:**
- Contextualizes answer to user's question
- Provides actionable recommendations for use case
- Mentions specific times and prices
- **Fallback mechanism:** Rule-based formatting when LLM unavailable

**Example Usage:**
```python
from src.llm_formatter import create_formatter

formatter = create_formatter()
response = formatter.format_response(
    user_question="When should I charge my EV?",
    data_source="today",
    analysis=analysis_dict,
    use_case="EV charging"
)
# Returns: "The cheapest hour is 2:00 at €70/MWh. I recommend..."
```

### 4. **Enhanced Agent** (`src/agent.py`)

**Workflow:**
1. Route Query → Detect if today or historical
2. Fetch Data → From aWATTar API or MCP Server
3. Clean Data → Remove nulls, normalize
4. Analyze → Calculate statistics and patterns
5. Format Response → Convert to natural language

**Key Nodes:**
- `route_query_node()` - Uses router to classify
- `fetch_prices_with_routing()` - Dynamically chooses data source
- `format_response_node()` - Uses formatter for output

## Data Flow Examples

### Example 1: Today's Price Query
```
User: "When should I charge my EV today?"
  ↓
Router: Detects "today" keyword
  ↓
Agent: Routes to aWATTar API (live data)
  ↓
Process: Fetch 24 hours, analyze prices
  ↓
Formatter: "The cheapest hour is 2:00 AM at €70/MWh..."
```

### Example 2: Historical Query
```
User: "What were prices like in January?"
  ↓
Router: Detects "January" → Sets date range
  ↓
Agent: Routes to MCP Server (PostgreSQL)
  ↓
MCP: Queries 31 days of historical data
  ↓
Process: Analyze trends, find patterns
  ↓
Formatter: "January averaged €104/MWh with..."
```

## Setup & Configuration

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key (optional - system works with fallbacks)
export OPENAI_API_KEY="sk-..."

# Ensure PostgreSQL is running with energy_prices database
# See .env for database configuration
```

### Environment Variables
```env
# Database Configuration (required)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=energy_prices
DB_USER=shubhangimore

# OpenAI API Key (optional - works without for fallback mode)
OPENAI_API_KEY=sk-...
```

## Testing

### Run Full Test Suite
```bash
python test_mcp_integration.py
```

**Tests:**
1. ✓ LLM Router - Query classification
2. ✓ MCP Server - Historical data queries
3. ✓ Response Formatter - Natural language generation
4. ✓ Full Agent - End-to-end workflow

### Individual Component Tests
```bash
# Test MCP Server only
python -c "from src.mcp_server import get_mcp_server; server = get_mcp_server(); print(server.query_historical_prices('2026-01-12', '2026-01-12'))"

# Test Router only
python -c "from src.llm_router import create_router; r = create_router(); print(r.detect_date_range('When was January?'))"
```

## Interview Talking Points

### 1. **Architecture & Design**
- **What:** MCP as a data abstraction layer
- **Why:** Separates concerns - data access from logic
- **How:** Tools expose database queries in structured format
- **Benefit:** Easy to extend with new data sources

### 2. **Intelligent Routing**
- **Problem:** Different questions need different data
- **Solution:** LLM classifies query intent
- **Advantage:** Handles natural language without hardcoding
- **Fallback:** Regex patterns ensure reliability

### 3. **Database Integration**
- **Setup:** PostgreSQL with 6 months historical data
- **Query:** SQL-based filtering by date/hour
- **Performance:** Indexed queries for fast retrieval
- **Scalability:** Ready to add more data sources

### 4. **Error Handling & Resilience**
- **API Key:** Works with or without OpenAI key
- **Failed Queries:** Graceful fallback to rule-based logic
- **Missing Data:** Clear error messages
- **Availability:** System degrades gracefully

### 5. **Production Patterns**
- **Modular Design:** Each component testable independently
- **Separation of Concerns:** Routing ≠ Fetching ≠ Formatting
- **Extensibility:** Add new tools/data sources easily
- **Observability:** Logging at each stage

## Future Enhancements

1. **Multi-Source Support**
   - Add weather API for demand predictions
   - Add grid load data for context
   - Add carbon intensity data

2. **Advanced Analytics**
   - Trend analysis (price increasing/decreasing)
   - Anomaly detection (unusual price spikes)
   - Forecasting (predict future prices)

3. **Optimization Tools**
   - Schedule finder (best 2-hour window for task)
   - Cost calculator (savings projection)
   - Alerts (notify when price drops)

4. **Multi-Agent Support**
   - Multiple agents querying same MCP server
   - Load balancing across database
   - Caching layer for common queries

## File Structure

```
energy-price-agent/
├── app.py                      # Streamlit UI
├── src/
│   ├── agent.py               # Enhanced agent with routing
│   ├── llm_router.py          # Query classification (NEW)
│   ├── llm_formatter.py       # Response generation (NEW)
│   ├── mcp_server.py          # MCP tools (NEW)
│   ├── data_sources.py        # API & DB access
│   ├── tools.py               # Pipeline tools
│   ├── analysis.py            # Price analysis
│   ├── preprocessing.py       # Data cleaning
│   ├── config.py              # Configuration
│   └── logger.py              # Logging
├── test_mcp_integration.py    # Component tests (NEW)
├── test_db_setup.py           # Database setup
├── requirements.txt           # Dependencies
├── .env                       # Environment config
└── README.md
```

## Key Takeaways

✅ **Shows MCP Understanding:**
- MCP as tool orchestration layer
- How to abstract complex operations
- When to use MCP (data sources)

✅ **Shows LLM Integration:**
- Intelligent query routing
- Semantic understanding of queries
- Graceful fallbacks

✅ **Shows Production Patterns:**
- Modular architecture
- Error handling
- Extensibility
- Testing

✅ **Shows Problem-Solving:**
- Identified need for smart routing
- Designed solution with fallbacks
- Tested thoroughly
- Documented for maintainability
