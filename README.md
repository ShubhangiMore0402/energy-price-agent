# Energy Price Intelligence Agent

An AI-powered energy optimization assistant built using **LangGraph, Python, Streamlit, and live electricity market APIs**.

The application helps users identify the most cost-effective hours to consume electricity based on live energy market prices and provides actionable recommendations for common household use cases such as EV charging, battery storage optimization, heat pumps, and appliance scheduling.

---

## Features

### Live Electricity Price Analysis

* Retrieves electricity market prices through API integration.
* Supports real-time energy price monitoring.
* Standardized data processing pipeline for future multi-source integrations.

### AI Agent Workflow (LangGraph)

The application is built as a modular AI workflow using LangGraph.

Workflow:

Fetch Prices
→ Clean Data
→ Analyze Prices
→ Generate Recommendation

Each stage is implemented as an independent tool node, making the workflow scalable and easy to maintain.

### Intelligent Recommendations

Users can ask questions such as:

* When is electricity cheapest today?
* Which hours should I avoid?
* How much can I save by shifting my usage?
* What is the average electricity price?

Recommendations adapt to the selected use case:

* EV Charging
* Battery Charging
* Heat Pump
* Washing Machine
* Dishwasher

### Cost Saving Estimation

The application estimates potential savings by shifting flexible energy consumption from peak-price periods to low-price periods.

### Interactive Dashboard

Built using Streamlit with:

* KPI cards
* Interactive price trend chart
* Cheapest hours analysis
* Most expensive hours analysis
* Optional technical details section

---

## Architecture

```text
Streamlit UI
      ↓
LangGraph Agent
      ↓
Fetch Price Tool
      ↓
Energy Price API
      ↓
Preprocessing
      ↓
Price Analysis
      ↓
Recommendation Engine
      ↓
User Dashboard
```

Project Structure

```text
energy-price-agent/
│
├── app.py
│
├── src/
│   ├── config.py
│   ├── data_sources.py
│   ├── preprocessing.py
│   ├── analysis.py
│   ├── tools.py
│   ├── agent.py
│   ├── logger.py
│   └── __init__.py
│
├── .env
├── requirements.txt
└── README.md
```

---

## Tech Stack

### Backend

* Python
* Pandas
* Requests

### AI Workflow

* LangGraph

### Frontend

* Streamlit
* Plotly

### Data Sources

* aWATTar Energy Market API
* Future Support:

  * ENTSO-E
  * SMARD

### Engineering Practices

* Modular architecture
* Structured logging
* Environment variable management
* Error handling
* Fallback mechanisms
* Reusable workflow design

---

## Example Use Cases

### EV Charging

Question:

"When is the cheapest time to charge my EV today?"

Output:

"The cheapest hours are 11:00, 12:00 and 13:00. Scheduling EV charging during these hours can reduce electricity costs."

---

### Cost Optimization

Question:

"How much can I save by shifting usage?"

Output:

"By moving approximately 10 kWh of flexible consumption from the highest-priced hour to the lowest-priced hour, you could save approximately €X today."

---

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd energy-price-agent
```

Create virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run app.py
```

---

## Future Enhancements

* OpenAI-powered recommendation engine
* Multi-agent architecture
* ENTSO-E integration
* SMARD integration
* Battery optimization scenarios
* Solar generation forecasting
* Energy trading insights
* Supabase integration
* User-specific energy consumption profiles

---

## Why This Project?

This project demonstrates practical skills relevant to modern AI, automation, and business engineering roles:

* API Integrations
* Workflow Automation
* LangGraph Agent Development
* Data Engineering
* Python Development
* Data Analysis
* Interactive Dashboarding
* Observability & Logging
* Production-Oriented Architecture

The goal is not only to retrieve electricity prices but to transform raw market data into actionable energy optimization insights.
