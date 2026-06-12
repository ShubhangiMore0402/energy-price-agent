import sys
from pathlib import Path
import pandas as pd
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

    daily_statistics = []
    most_expensive_day = None
    cheapest_day = None

    if "timestamp" in df.columns:
        daily_df = df.copy()
        daily_df["date"] = pd.to_datetime(daily_df["timestamp"]).dt.date
        daily_df["month"] = pd.to_datetime(daily_df["timestamp"]).dt.to_period("M").astype(str)
        daily_summary = (
            daily_df.groupby("date", as_index=False)["price_eur_mwh"]
            .mean()
            .rename(columns={"price_eur_mwh": "avg_price"})
            .sort_values("avg_price", ascending=False)
        )

        monthly_best_hours = []
        monthly_summary = []
        for month, month_df in daily_df.groupby("month"):
            month_cheapest = month_df.nsmallest(1, "price_eur_mwh")
            if not month_cheapest.empty:
                best_row = month_cheapest.iloc[0]
                monthly_best_hours.append({
                    "month": month,
                    "date": str(pd.to_datetime(best_row["timestamp"]).date()),
                    "hour": int(best_row["hour"]),
                    "price_eur_mwh": round(float(best_row["price_eur_mwh"]), 2),
                })

            monthly_summary.append({
                "month": month,
                "avg_price": round(float(month_df["price_eur_mwh"].mean()), 2),
                "min_price": round(float(month_df["price_eur_mwh"].min()), 2),
                "max_price": round(float(month_df["price_eur_mwh"].max()), 2),
            })

        daily_statistics = daily_summary.to_dict("records")
        if not daily_summary.empty:
            most_expensive_day = daily_summary.iloc[0].to_dict()
            cheapest_day = daily_summary.sort_values("avg_price", ascending=True).iloc[0].to_dict()

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
        "daily_statistics": daily_statistics,
        "monthly_summary": monthly_summary,
        "monthly_best_hours": monthly_best_hours,
        "most_expensive_day": most_expensive_day,
        "cheapest_day": cheapest_day,
        "estimated_saving_eur": estimated_saving_eur,
        "example_kwh": example_kwh,
    }


def create_recommendation(analysis, question, use_case, date):
    cheapest_hours = [str(item["hour"]) for item in analysis["cheapest_hours"]]
    expensive_hours = [str(item["hour"]) for item in analysis["expensive_hours"]]
    question_lower = question.lower()
    is_compare_question = "compare" in question_lower

    is_day_question = "day" in question_lower or "daily" in question_lower

    if is_compare_question and analysis.get("monthly_best_hours"):
        month_lines = []
        for item in analysis["monthly_best_hours"]:
            month_lines.append(
                f"{item['month']}: {item['hour']}:00 on {item['date']} at €{item['price_eur_mwh']}/MWh"
            )
        return (
            f"Here is the comparison for {use_case}: "
            + "; ".join(month_lines)
            + "."
        )

    if is_day_question and analysis.get("most_expensive_day"):
        day = analysis["most_expensive_day"]
        return (
            f"The most expensive day in the selected period was {day['date']} "
            f"with an average price of €{round(day['avg_price'], 2)}/MWh."
        )

    if is_day_question and analysis.get("cheapest_day"):
        day = analysis["cheapest_day"]
        return (
            f"The cheapest day in the selected period was {day['date']} "
            f"with an average price of €{round(day['avg_price'], 2)}/MWh."
        )

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