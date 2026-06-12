"""
LLM Router for intelligent query routing
Routes queries to appropriate data source (live API or historical database)
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import re

try:
    from .logger import logger
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.logger import logger


class QueryRouter:
    """Routes user queries to appropriate data source"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the router with an LLM
        
        Args:
            model: OpenAI model to use (default: gpt-4o-mini for cost-effectiveness)
        """
        try:
            self.llm = ChatOpenAI(model=model, temperature=0)
            self.llm_available = True
        except Exception as e:
            logger.warning(f"LLM not available: {e}. Using fallback date detection.")
            self.llm = None
            self.llm_available = False
        
        self.today = datetime.now().date()
    
    def detect_date_range(self, user_question: str, selected_date: Optional[str] = None) -> dict:
        """
        Use LLM to detect date range from natural language question
        
        Args:
            user_question: The user's question
        
        Returns:
            dict with:
                - query_type: "today" | "historical" | "both"
                - start_date: YYYY-MM-DD or None
                - end_date: YYYY-MM-DD or None
                - specific_hour: int or None
                - reasoning: explanation of the detection
        """
        
        anchor_date = selected_date if selected_date and selected_date != str(self.today) else None

        compare_range = self._extract_month_comparison(user_question, anchor_date=anchor_date)
        if compare_range:
            return compare_range

        explicit_range = self._extract_relative_range(user_question, anchor_date=anchor_date)
        if explicit_range:
            return explicit_range

        # If the sidebar date points to a historical day, prefer that selected date
        # only when the question does not already specify a time range.
        if selected_date and selected_date != str(self.today):
            return {
                "query_type": "historical",
                "start_date": selected_date,
                "end_date": selected_date,
                "specific_hour": None,
                "reasoning": f"Using selected analysis date {selected_date}"
            }

        # If LLM not available, use fallback immediately
        if not self.llm_available:
            logger.info("Using fallback date detection (LLM unavailable)")
            return self._fallback_date_detection(user_question)
        
        prompt = PromptTemplate.from_template("""
You are a date extraction assistant for energy price queries.

Analyze this question and determine:
1. Is it asking about TODAY, HISTORICAL data, or BOTH?
2. Extract specific dates if mentioned (YYYY-MM-DD format)
3. Extract specific hours if mentioned (0-23)

Today's date is: {today}

Question: "{question}"

Return ONLY valid JSON (no markdown, no extra text):
{{
    "query_type": "today" or "historical" or "both",
    "start_date": "YYYY-MM-DD" or null,
    "end_date": "YYYY-MM-DD" or null,
    "specific_hour": integer (0-23) or null,
    "reasoning": "brief explanation"
}}

Examples:
- "What are prices today?" → {{"query_type": "today", "start_date": null, "end_date": null}}
- "When were prices high in January?" → {{"query_type": "historical", "start_date": "2026-01-01", "end_date": "2026-01-31"}}
- "Compare today with last week" → {{"query_type": "both", "start_date": "2026-06-04", "end_date": "2026-06-11"}}
- "What hour 14 prices were like?" → {{"query_type": "historical", "specific_hour": 14}}
        """)
        
        try:
            logger.info(f"Routing query: {user_question[:50]}...")
            
            response = self.llm.invoke(prompt.format(
                today=self.today,
                question=user_question
            ))
            
            # Extract JSON from response
            response_text = response.content.strip()
            
            # Try to parse JSON
            result = json.loads(response_text)
            
            logger.info(f"Route detected: {result['query_type']}")
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {response_text}")
            # Fallback: try regex patterns
            return self._fallback_date_detection(user_question)
        
        except Exception as e:
            logger.error(f"LLM routing failed: {e}")
            return self._fallback_date_detection(user_question)
    
    def _fallback_date_detection(self, question: str) -> dict:
        """
        Fallback date detection using regex patterns
        Used when LLM fails
        """
        question_lower = question.lower()
        
        # Check for today/current
        if any(word in question_lower for word in ["today", "now", "current", "right now", "this moment"]):
            return {
                "query_type": "today",
                "start_date": None,
                "end_date": None,
                "specific_hour": None,
                "reasoning": "Detected 'today' keyword"
            }
        
        # Check for month names
        months = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12"
        }
        
        for month_name, month_num in months.items():
            if month_name in question_lower:
                start_date = f"2026-{month_num}-01"
                end_date = f"2026-{month_num}-28"
                return {
                    "query_type": "historical",
                    "start_date": start_date,
                    "end_date": end_date,
                    "specific_hour": None,
                    "reasoning": f"Detected {month_name.capitalize()}"
                }
        
        # Check for week/day keywords
        if "week" in question_lower or "last 7" in question_lower:
            end = self.today
            start = end - timedelta(days=7)
            return {
                "query_type": "historical",
                "start_date": str(start),
                "end_date": str(end),
                "specific_hour": None,
                "reasoning": "Detected 'week' keyword"
            }

        explicit_range = self._extract_relative_range(question)
        if explicit_range:
            return explicit_range
        
        # Default to today
        return {
            "query_type": "today",
            "start_date": None,
            "end_date": None,
            "specific_hour": None,
            "reasoning": "No specific date detected, defaulting to today"
        }

    def _extract_month_comparison(self, question: str, anchor_date: Optional[str] = None) -> dict:
        """
        Detect comparison questions that mention two distinct months.
        Example: 'Compare the cheapest EV charging hours in April and May'
        """
        question_lower = question.lower()
        month_names = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]

        present_months = [month for month in month_names if month in question_lower]
        if "compare" in question_lower and len(present_months) >= 2:
            month_to_num = {
                "january": "01", "february": "02", "march": "03", "april": "04",
                "may": "05", "june": "06", "july": "07", "august": "08",
                "september": "09", "october": "10", "november": "11", "december": "12"
            }

            first_month = present_months[0]
            second_month = present_months[1]

            # Use the current year unless the anchor date points elsewhere.
            year = datetime.fromisoformat(anchor_date).year if anchor_date else self.today.year

            start_date = f"{year}-{month_to_num[first_month]}-01"
            if second_month == "february":
                end_day = 28
            elif second_month in ["april", "june", "september", "november"]:
                end_day = 30
            else:
                end_day = 31
            end_date = f"{year}-{month_to_num[second_month]}-{end_day:02d}"

            return {
                "query_type": "historical",
                "start_date": start_date,
                "end_date": end_date,
                "specific_hour": None,
                "comparison_months": [first_month.capitalize(), second_month.capitalize()],
                "reasoning": f"Detected comparison between {first_month.capitalize()} and {second_month.capitalize()}"
            }

        return {}

    def _has_explicit_date_reference(self, question: str) -> bool:
        """
        Detect whether the user question explicitly mentions a date/time reference.
        """
        question_lower = question.lower()

        explicit_keywords = [
            "today", "now", "current", "right now", "this moment",
            "yesterday", "tomorrow", "last week", "this week", "last month",
        ]
        if any(keyword in question_lower for keyword in explicit_keywords):
            return True

        month_names = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]
        if any(month in question_lower for month in month_names):
            return True

        date_pattern = r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b"
        if re.search(date_pattern, question_lower):
            return True

        return False

    def _extract_relative_range(self, question: str, anchor_date: Optional[str] = None) -> dict:
        """
        Extract relative date ranges like 'past 1 month' or 'last 30 days'.
        Returns an empty dict when no explicit range is found.
        """
        question_lower = question.lower()
        anchor = datetime.fromisoformat(anchor_date).date() if anchor_date else self.today

        month_patterns = [
            r"\b(past|last|previous)\s+(1|one)\s+month\b",
            r"\b(past|last|previous)\s+month\b",
            r"\b(last|past|previous)\s+(\d+)\s+months?\b",
            r"\blast\s+30\s+days\b",
            r"\bpast\s+30\s+days\b",
        ]

        match = None
        for pattern in month_patterns:
            match = re.search(pattern, question_lower)
            if match:
                break

        if match:
            if len(match.groups()) >= 2 and match.group(2) and match.group(2).isdigit():
                months_back = int(match.group(2))
                days_back = 30 * months_back
            else:
                days_back = 30

            end = anchor
            start = end - timedelta(days=days_back)
            return {
                "query_type": "historical",
                "start_date": str(start),
                "end_date": str(end),
                "specific_hour": None,
                "reasoning": f"Detected relative range anchored to {str(end)}"
            }

        return {}
    
    def should_use_live_api(self, route_info: dict) -> bool:
        """
        Determine if live API (aWATTar) should be used
        
        Args:
            route_info: Output from detect_date_range()
        
        Returns:
            bool: True if should use live API, False if use historical DB
        """
        if route_info["query_type"] == "today":
            return True
        elif route_info["query_type"] == "both":
            return True  # We'll handle "both" specially in agent
        else:
            return False
    
    def format_for_mcp(self, route_info: dict) -> dict:
        """
        Format routing info for MCP tool parameters
        
        Args:
            route_info: Output from detect_date_range()
        
        Returns:
            dict with properly formatted MCP parameters
        """
        if not route_info["start_date"]:
            route_info["start_date"] = str(self.today - timedelta(days=7))
        if not route_info["end_date"]:
            route_info["end_date"] = str(self.today)
        
        return {
            "start_date": route_info["start_date"],
            "end_date": route_info["end_date"],
            "hour": route_info.get("specific_hour")
        }


def create_router() -> QueryRouter:
    """Factory function to create router instance"""
    return QueryRouter()
