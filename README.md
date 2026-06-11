# Energy Price Intelligence Agent

An AI-powered energy price analysis application built using **LangGraph, Python, Streamlit, and the aWATTar Electricity Market API**.

The application helps users identify cost-effective time windows for electricity consumption by analyzing hourly electricity market prices and generating recommendations tailored to specific household use cases such as EV charging, battery charging, heat pumps, dishwashers, and washing machines.

---

# Features

## Electricity Price Analysis

* Retrieves hourly electricity market prices from the public aWATTar API.
* Supports date-based analysis using user-selected dates.
* Standardized data processing pipeline for future data source integrations.
* Automatic validation of API responses before analysis.

---

## AI Workflow using LangGraph

The application is implemented as a modular workflow using LangGraph.

Workflow:

```text
Fetch Prices
    ↓
Clean Data
    ↓
Analyze Prices
    ↓
Generate Recommendation
```

Each stage is implemented as an independent tool node, making the workflow modular, maintainable, and extensible.

---

## Intelligent Recommendations

Users can ask questions such as:

* When is electricity cheapest today?
* Which hours should I avoid?
* What is the average electricity price?
* How much can I save by shifting usage?

Recommendations adapt dynamically based on:

* User question
* Selected date
* Selected use case

Supported use cases:

* EV Charging
* Battery Charging
* Heat Pump
* Dishwasher
* Washing Machine

---

## Cost Saving Estimation

The application estimates potential savings by shifting flexible electricity consumption from expensive hours to cheaper hours.

Example:

* Determine highest-price hour
* Determine lowest-price hour
* Estimate savings for a configurable energy consumption profile

---

## Interactive Dashboard

Built with Streamlit and Plotly.

Features include:

* Recommendation panel
* KPI cards
* Price trend visualization
* Cheapest-hour analysis
* Most-expensive-hour analysis
* Optional technical details section

---

# Architecture

```text
Streamlit UI
      ↓
LangGraph Agent
      ↓
Fetch Price Tool
      ↓
aWATTar API
      ↓
Data Cleaning
      ↓
Price Analysis
      ↓
Recommendation Engine
      ↓
User Dashboard
```

---

# Project Structure

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
├── requirements.txt
└── README.md
```

---

# Tech Stack

## Backend

* Python
* Pandas
* Requests

## Workflow Orchestration

* LangGraph

## Frontend

* Streamlit
* Plotly

## Data Source

### aWATTar Electricity Market API

Public API endpoint:

https://api.awattar.de/v1/marketdata

Data used:

* start_timestamp
* end_timestamp
* marketprice

No authentication or API key is required.

---

# Engineering Concepts Demonstrated

This project demonstrates:

* API integration
* JSON parsing
* Workflow orchestration
* Data preprocessing
* Data analysis
* Error handling
* Logging and observability
* Modular architecture
* Interactive dashboards

---

# Example Use Cases

## EV Charging

Question:

"When is the cheapest time to charge my EV?"

Example Output:

"The cheapest hours for the selected date are 11:00, 12:00, and 13:00. These are the most cost-effective hours for EV charging."

---

## Cost Optimization

Question:

"How much can I save by shifting usage?"

Example Output:

"Shifting approximately 10 kWh from the most expensive hour to the cheapest hour could save approximately €X for the selected day."

---

# Installation

Clone repository:

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

Run application:

```bash
streamlit run app.py
```

---

# Future Enhancements

* ENTSO-E integration
* SMARD integration
* Multi-source comparison
* Battery optimization scenarios
* Solar generation forecasting
* Home energy management scenarios
* Supabase persistence layer
* User-specific consumption profiles
* LLM-powered recommendation generation

---

# Why This Project?

The objective of this project is to demonstrate practical skills required for modern AI, automation, and business engineering roles.

Key skills showcased:

* Python Development
* API Integration
* LangGraph Agent Development
* Workflow Automation
* Data Engineering
* Data Analysis
* Dashboard Development
* Error Handling
* Logging & Observability
* Production-Oriented Design

Rather than simply displaying electricity prices, the application transforms raw market data into actionable energy optimization insights that can support smarter energy consumption decisions.
