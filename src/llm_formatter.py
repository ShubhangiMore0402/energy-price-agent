import json
from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

try:
    from .logger import logger
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.logger import logger


class ResponseFormatter:
    """Formats analysis results into natural language responses"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize formatter with an LLM
        
        Args:
            model: OpenAI model to use
        """
        try:
            self.llm = ChatOpenAI(model=model, temperature=0.7)
            self.llm_available = True
        except Exception as e:
            logger.warning(f"LLM not available: {e}. Using fallback formatting.")
            self.llm = None
            self.llm_available = False
    
    def format_response(
        self,
        user_question: str,
        data_source: str,
        analysis: Dict[str, Any],
        use_case: str,
        raw_data: Any = None
    ) -> str:
        """
        Format analysis results into a natural language response
        
        Args:
            user_question: Original user question
            data_source: "today" | "historical" | "both"
            analysis: Analysis dict with prices, trends, etc.
            use_case: The use case (EV charging, dishwasher, etc.)
            raw_data: Optional raw price data for context
        
        Returns:
            str: Formatted response
        """
        
        # If LLM not available, use fallback
        if not self.llm_available:
            logger.info("Using fallback formatting (LLM unavailable)")
            return self._fallback_format(analysis, user_question, use_case, data_source)
        
        # Prepare context from analysis
        context = self._prepare_context(analysis, data_source, raw_data)
        
        prompt = PromptTemplate.from_template("""
You are a friendly energy price advisor assistant. Format the following data into a natural, helpful response.

User's Question: "{question}"
Use Case: {use_case}
Data Source: {data_source} (today's live data or historical data)

Price Analysis:
{context}

Guidelines:
1. Answer the user's question directly and conversationally
2. Provide actionable recommendations for {use_case}
3. Mention specific times/prices when relevant
4. Keep response concise (2-3 sentences for direct answers, 1 paragraph for detailed)
5. If historical: mention the time period analyzed
6. If live: mention prices are current as of now
7. Include money-saving tips when relevant

Response:
        """)
        
        try:
            logger.info(f"Formatting response for: {user_question[:50]}...")
            
            response = self.llm.invoke(prompt.format(
                question=user_question,
                use_case=use_case,
                data_source=data_source,
                context=context
            ))
            
            formatted = response.content.strip()
            logger.info("Response formatted successfully")
            
            return formatted
        
        except Exception as e:
            logger.error(f"Formatting failed: {e}")
            return self._fallback_format(analysis, user_question, use_case, data_source)
    
    def _prepare_context(
        self,
        analysis: Dict[str, Any],
        data_source: str,
        raw_data: Any = None
    ) -> str:
        """
        Prepare analysis context for LLM
        
        Args:
            analysis: Analysis results
            data_source: "today" or "historical"
            raw_data: Optional raw price data
        
        Returns:
            str: Formatted context
        """
        context_parts = []
        
        # Price statistics
        if "average_price" in analysis:
            context_parts.append(f"- Average Price: €{analysis['average_price']}/MWh")
        if "min_price" in analysis:
            context_parts.append(f"- Minimum Price: €{analysis['min_price']}/MWh")
        if "max_price" in analysis:
            context_parts.append(f"- Maximum Price: €{analysis['max_price']}/MWh")
        
        # Cheapest hours
        if "cheapest_hours" in analysis:
            cheapest = analysis["cheapest_hours"][:3]
            hours_str = ", ".join([f"{h['hour']}:00 (€{h['price_eur_mwh']}/MWh)" for h in cheapest])
            context_parts.append(f"- Cheapest Hours: {hours_str}")
        
        # Expensive hours
        if "expensive_hours" in analysis:
            expensive = analysis["expensive_hours"][:3]
            hours_str = ", ".join([f"{h['hour']}:00 (€{h['price_eur_mwh']}/MWh)" for h in expensive])
            context_parts.append(f"- Most Expensive Hours: {hours_str}")
        
        # Savings
        if "estimated_saving_eur" in analysis:
            context_parts.append(
                f"- Potential Saving: €{analysis['estimated_saving_eur']} for "
                f"{analysis.get('example_kwh', 10)}kWh shift"
            )
        
        # Data period
        if data_source == "historical":
            context_parts.append("- Data: Historical (past period)")
        else:
            context_parts.append("- Data: Live (current day)")
        
        return "\n".join(context_parts)
    
    def _fallback_format(
        self,
        analysis: Dict[str, Any],
        question: str,
        use_case: str,
        data_source: str
    ) -> str:
        """
        Fallback formatting when LLM fails
        Returns a simple formatted response
        """
        response_parts = []
        
        # Answer the question type
        question_lower = question.lower()
        is_compare_question = "compare" in question_lower
        is_day_question = "day" in question_lower or "daily" in question_lower

        if is_compare_question and data_source == "historical" and analysis.get("monthly_best_hours"):
            month_lines = [
                f"{item['month']}: cheapest hour {item['hour']}:00 on {item['date']} at €{item['price_eur_mwh']}/MWh"
                for item in analysis["monthly_best_hours"]
            ]
            response_parts.append(
                "Comparison across the selected months: " + "; ".join(month_lines) + "."
            )
            return " ".join(response_parts)

        if is_day_question and data_source == "historical":
            if any(keyword in question_lower for keyword in ["cheap", "cheapest", "lowest", "minimum", "min"]):
                day = analysis.get("cheapest_day")
                if day:
                    response_parts.append(
                        f"During the analyzed period, the cheapest day was {day['date']} with an average price of €{round(day['avg_price'], 2)}/MWh."
                    )
            else:
                day = analysis.get("most_expensive_day")
                if day:
                    response_parts.append(
                        f"During the analyzed period, the most expensive day was {day['date']} with an average price of €{round(day['avg_price'], 2)}/MWh."
                    )

            if response_parts:
                return " ".join(response_parts)

        if not response_parts and any(keyword in question_lower for keyword in ["cheap", "cheapest", "lowest", "minimum", "min"]):
            cheapest = analysis.get("cheapest_hours", [])
            if cheapest:
                hour = cheapest[0]["hour"]
                price = cheapest[0]["price_eur_mwh"]
                if data_source == "historical":
                    timestamp = cheapest[0].get("timestamp")
                    if timestamp:
                        response_parts.append(
                            f"During the analyzed period, the lowest price was at {hour}:00 on {str(timestamp)[:10]} at €{price}/MWh."
                        )
                    else:
                        response_parts.append(
                            f"During the analyzed period, the lowest price was at {hour}:00 at €{price}/MWh."
                        )
                else:
                    response_parts.append(
                        f"The cheapest hour is {hour}:00 at €{price}/MWh."
                    )
        
        elif "expensive" in question_lower or "avoid" in question_lower:
            expensive = analysis.get("expensive_hours", [])
            if expensive:
                hour = expensive[0]["hour"]
                price = expensive[0]["price_eur_mwh"]
                if data_source == "historical":
                    response_parts.append(
                        f"During the analyzed period, the most expensive hour was {hour}:00 at €{price}/MWh. "
                        f"I'd recommend avoiding this time for {use_case}."
                    )
                else:
                    response_parts.append(
                        f"The most expensive hour is {hour}:00 at €{price}/MWh. "
                        f"I'd recommend avoiding this time for {use_case}."
                    )
        
        elif not response_parts:
            # Generic response
            avg = analysis.get("average_price", "N/A")
            min_p = analysis.get("min_price", "N/A")
            if data_source == "historical":
                response_parts.append(
                    f"In the analyzed period, the average electricity price was €{avg}/MWh, "
                    f"ranging from €{min_p}/MWh to €{analysis.get('max_price', 'N/A')}/MWh."
                )
            else:
                response_parts.append(
                    f"Today's average electricity price is €{avg}/MWh, "
                    f"ranging from €{min_p}/MWh to €{analysis.get('max_price', 'N/A')}/MWh."
                )
        
        # Add savings tip
        if "estimated_saving_eur" in analysis:
            saving = analysis["estimated_saving_eur"]
            response_parts.append(
                f"By shifting your {use_case} to cheaper hours, you could save €{saving}."
            )
        
        return " ".join(response_parts)


def create_formatter() -> ResponseFormatter:
    """Factory function to create formatter instance"""
    return ResponseFormatter()
