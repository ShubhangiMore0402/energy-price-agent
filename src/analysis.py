import sys
from pathlib import Path
try:
    from .logger import logger
except ImportError:
    # If relative imports fail, add parent directory to path for direct execution
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.logger import logger

def analyze_prices(df):
    logger.info(f"Starting price analysis | rows={len(df)}")

    cheapest_hours = df.nsmallest(3, "price_eur_mwh")
    expensive_hours = df.nlargest(3, "price_eur_mwh")

    avg_price = round(df["price_eur_mwh"].mean(), 2)
    min_price = round(df["price_eur_mwh"].min(), 2)
    max_price = round(df["price_eur_mwh"].max(), 2)

    # Example saving for shifting 10 kWh usage from most expensive to cheapest hour
    example_kwh = 10
    estimated_saving_eur = round(((max_price - min_price) / 1000) * example_kwh, 2)

    logger.info("Price analysis completed")

    return {
        "average_price": avg_price,
        "min_price": min_price,
        "max_price": max_price,
        "cheapest_hours": cheapest_hours.to_dict("records"),
        "expensive_hours": expensive_hours.to_dict("records"),
        "estimated_saving_eur": estimated_saving_eur,
        "example_kwh": example_kwh,
    }


def create_recommendation(analysis, question, use_case, date):
    cheapest_hours = [str(item["hour"]) for item in analysis["cheapest_hours"]]
    expensive_hours = [str(item["hour"]) for item in analysis["expensive_hours"]]

    question_lower = question.lower()

    if "expensive" in question_lower or "avoid" in question_lower:
        return (
            f"The most expensive hours are {', '.join(expensive_hours)}:00. "
            f"For {use_case}, I would avoid these hours if possible."
        )

    if "saving" in question_lower or "save" in question_lower or "cost" in question_lower:
        return (
            f"For {use_case}, shifting around {analysis['example_kwh']} kWh from the most expensive hour "
            f"to the cheapest hour could save approximately €{analysis['estimated_saving_eur']} today."
        )

    if "average" in question_lower:
        return (
            f"The average electricity price for the selected period is "
            f"{analysis['average_price']} €/MWh."
        )

    return (
        f"The cheapest hours are {', '.join(cheapest_hours)}:00. "
        f"For {use_case}, these are the best hours to schedule flexible energy usage."
    )