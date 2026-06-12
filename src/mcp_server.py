import json
from datetime import datetime, timedelta
from typing import Any
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

try:
    from .config import DATABASE_URL
    from .logger import logger
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.config import DATABASE_URL
    from src.logger import logger


class HistoricalPriceServer:
    """MCP Server providing historical price query tools"""
    
    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url
        self.engine = create_engine(db_url, echo=False)

    def _format_sql_for_log(self, query: str) -> str:
        return " ".join(query.split())

    def _log_sql_query(self, query_name: str, query: str, params: dict) -> None:
        logger.info(
            f"SQL QUERY | {query_name} | query={self._format_sql_for_log(query)} | params={params}"
        )

    def _log_sql_response(self, query_name: str, rows: list, preview_limit: int = 5) -> None:
        preview = rows[:preview_limit]
        logger.info(
            f"SQL RESPONSE | {query_name} | row_count={len(rows)} | preview={json.dumps(preview, default=str)}"
        )
    
    def query_historical_prices(
        self, 
        start_date: str, 
        end_date: str,
        hour: int = None
    ) -> dict:
        """
        Query historical electricity prices from PostgreSQL
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            hour: Optional specific hour (0-23)
        
        Returns:
            dict with price data and statistics
        """
        try:
            logger.info(
                f"MCP QUERY | historical_prices | start_date={start_date} | end_date={end_date} | hour={hour}"
            )
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            
            with self.engine.connect() as connection:
                if hour is not None:
                    query = text("""
                        SELECT timestamp, hour, price_eur_mwh, source
                        FROM electricity_prices
                        WHERE DATE(timestamp) >= :start_date 
                        AND DATE(timestamp) <= :end_date
                        AND EXTRACT(HOUR FROM timestamp) = :hour
                        ORDER BY timestamp
                    """)
                    result = connection.execute(query, {
                        "start_date": start,
                        "end_date": end,
                        "hour": hour
                    })
                else:
                    query = text("""
                        SELECT timestamp, hour, price_eur_mwh, source
                        FROM electricity_prices
                        WHERE DATE(timestamp) >= :start_date 
                        AND DATE(timestamp) <= :end_date
                        ORDER BY timestamp
                    """)
                    result = connection.execute(query, {
                        "start_date": start,
                        "end_date": end
                    })

                sql_query_text = query.text if hasattr(query, "text") else str(query)
                sql_params = {
                    "start_date": str(start.date()),
                    "end_date": str(end.date())
                }
                if hour is not None:
                    sql_params["hour"] = hour
                self._log_sql_query("historical_prices", sql_query_text, sql_params)
                
                rows = result.fetchall()

                response_preview = [
                    {
                        "timestamp": str(row[0]),
                        "hour": int(row[1]),
                        "price_eur_mwh": round(float(row[2]), 2),
                        "source": row[3],
                    }
                    for row in rows
                ]
                self._log_sql_response("historical_prices", response_preview)
                
                if not rows:
                    logger.info(
                        f"MCP QUERY RESULT | no_data | start_date={start_date} | end_date={end_date} | hour={hour}"
                    )
                    return {
                        "status": "no_data",
                        "message": f"No price data found for {start_date} to {end_date}",
                        "data": []
                    }
                
                df = pd.DataFrame(rows, columns=["timestamp", "hour", "price_eur_mwh", "source"])

                logger.info(
                    f"MCP QUERY RESULT | success | records={len(df)} | start_date={start_date} | end_date={end_date} | hour={hour}"
                )
                
                return {
                    "status": "success",
                    "date_range": f"{start_date} to {end_date}",
                    "records": len(df),
                    "data": df.to_dict("records"),
                    "statistics": {
                        "avg_price": round(df["price_eur_mwh"].mean(), 2),
                        "min_price": round(df["price_eur_mwh"].min(), 2),
                        "max_price": round(df["price_eur_mwh"].max(), 2),
                        "std_dev": round(df["price_eur_mwh"].std(), 2),
                    }
                }
        
        except Exception as e:
            logger.error(
                f"MCP QUERY RESULT | error | start_date={start_date} | end_date={end_date} | hour={hour} | error={e}"
            )
            return {
                "status": "error",
                "message": f"Query failed: {str(e)}",
                "data": []
            }
    
    def get_price_statistics(
        self,
        start_date: str,
        end_date: str
    ) -> dict:
        """
        Get aggregated price statistics for a date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            dict with price statistics by hour and day
        """
        try:
            logger.info(
                f"MCP QUERY | price_statistics | start_date={start_date} | end_date={end_date}"
            )
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            
            with self.engine.connect() as connection:
                # Overall statistics
                query = text("""
                    SELECT 
                        AVG(price_eur_mwh) as avg_price,
                        MIN(price_eur_mwh) as min_price,
                        MAX(price_eur_mwh) as max_price,
                        STDDEV(price_eur_mwh) as std_dev,
                        COUNT(*) as total_records,
                        DATE(timestamp) as date_count
                    FROM electricity_prices
                    WHERE DATE(timestamp) >= :start_date 
                    AND DATE(timestamp) <= :end_date
                    GROUP BY DATE(timestamp)
                    ORDER BY date_count
                """)
                
                result = connection.execute(query, {
                    "start_date": start,
                    "end_date": end
                })

                self._log_sql_query(
                    "price_statistics_daily",
                    query.text if hasattr(query, "text") else str(query),
                    {"start_date": str(start.date()), "end_date": str(end.date())}
                )
                
                daily_stats = result.fetchall()
                self._log_sql_response("price_statistics_daily", [
                    {
                        "avg_price": round(float(row[0]) if row[0] else 0, 2),
                        "min_price": round(float(row[1]) if row[1] else 0, 2),
                        "max_price": round(float(row[2]) if row[2] else 0, 2),
                        "std_dev": round(float(row[3]) if row[3] else 0, 2),
                        "total_records": int(row[4]) if row[4] is not None else 0,
                        "date_count": str(row[5]),
                    }
                    for row in daily_stats
                ])
                
                # Hourly average statistics
                hourly_query = text("""
                    SELECT 
                        EXTRACT(HOUR FROM timestamp) as hour,
                        AVG(price_eur_mwh) as avg_price,
                        MIN(price_eur_mwh) as min_price,
                        MAX(price_eur_mwh) as max_price,
                        COUNT(*) as count
                    FROM electricity_prices
                    WHERE DATE(timestamp) >= :start_date 
                    AND DATE(timestamp) <= :end_date
                    GROUP BY EXTRACT(HOUR FROM timestamp)
                    ORDER BY hour
                """)
                
                hourly_result = connection.execute(hourly_query, {
                    "start_date": start,
                    "end_date": end
                })
                
                hourly_stats = hourly_result.fetchall()
                self._log_sql_query(
                    "price_statistics_hourly",
                    hourly_query.text if hasattr(hourly_query, "text") else str(hourly_query),
                    {"start_date": str(start.date()), "end_date": str(end.date())}
                )
                self._log_sql_response("price_statistics_hourly", [
                    {
                        "hour": int(row[0]),
                        "avg_price": round(float(row[1]) if row[1] else 0, 2),
                        "min_price": round(float(row[2]) if row[2] else 0, 2),
                        "max_price": round(float(row[3]) if row[3] else 0, 2),
                        "count": int(row[4]),
                    }
                    for row in hourly_stats
                ])
                
                return {
                    "status": "success",
                    "date_range": f"{start_date} to {end_date}",
                    "daily_statistics": [
                        {
                            "date": str(row[5]),
                            "avg_price": round(float(row[0]) if row[0] else 0, 2),
                            "min_price": round(float(row[1]) if row[1] else 0, 2),
                            "max_price": round(float(row[2]) if row[2] else 0, 2),
                        }
                        for row in daily_stats
                    ],
                    "hourly_averages": [
                        {
                            "hour": int(row[0]),
                            "avg_price": round(float(row[1]) if row[1] else 0, 2),
                            "min_price": round(float(row[2]) if row[2] else 0, 2),
                            "max_price": round(float(row[3]) if row[3] else 0, 2),
                            "records": int(row[4])
                        }
                        for row in hourly_stats
                    ]
                }
        
        except Exception as e:
            logger.error(
                f"MCP QUERY RESULT | error | statistics | start_date={start_date} | end_date={end_date} | error={e}"
            )
            return {
                "status": "error",
                "message": f"Statistics query failed: {str(e)}"
            }
    
    def find_cheapest_hours(
        self,
        start_date: str,
        end_date: str,
        top_n: int = 5
    ) -> dict:
        """
        Find the cheapest hours in a date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            top_n: Number of cheapest hours to return (default: 5)
        
        Returns:
            dict with cheapest hour slots
        """
        try:
            logger.info(
                f"MCP QUERY | cheapest_hours | start_date={start_date} | end_date={end_date} | top_n={top_n}"
            )
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            
            with self.engine.connect() as connection:
                query = text("""
                    SELECT timestamp, hour, price_eur_mwh, source
                    FROM electricity_prices
                    WHERE DATE(timestamp) >= :start_date 
                    AND DATE(timestamp) <= :end_date
                    ORDER BY price_eur_mwh ASC
                    LIMIT :limit
                """)
                
                result = connection.execute(query, {
                    "start_date": start,
                    "end_date": end,
                    "limit": top_n
                })
                
                rows = result.fetchall()
                self._log_sql_query(
                    "cheapest_hours",
                    query.text if hasattr(query, "text") else str(query),
                    {"start_date": str(start.date()), "end_date": str(end.date()), "limit": top_n}
                )
                self._log_sql_response("cheapest_hours", [
                    {
                        "timestamp": str(row[0]),
                        "hour": int(row[1]),
                        "price_eur_mwh": round(float(row[2]), 2),
                        "source": row[3],
                    }
                    for row in rows
                ])
                
                return {
                    "status": "success",
                    "date_range": f"{start_date} to {end_date}",
                    "cheapest_hours": [
                        {
                            "timestamp": str(row[0]),
                            "hour": int(row[1]),
                            "price_eur_mwh": round(float(row[2]), 2),
                            "source": row[3]
                        }
                        for row in rows
                    ]
                }
        
        except Exception as e:
            logger.error(
                f"MCP QUERY RESULT | error | cheapest_hours | start_date={start_date} | end_date={end_date} | top_n={top_n} | error={e}"
            )
            return {
                "status": "error",
                "message": f"Cheapest hours query failed: {str(e)}"
            }


# Create a singleton instance for use in the application
_server_instance = None

def get_mcp_server() -> HistoricalPriceServer:
    """Get or create MCP server instance"""
    global _server_instance
    if _server_instance is None:
        _server_instance = HistoricalPriceServer()
    return _server_instance


# Tool definitions for LangChain integration
def create_mcp_tools():
    """
    Create tool definitions compatible with LangChain agents
    
    Returns:
        list of Tool objects
    """
    from langchain_core.tools import tool
    
    server = get_mcp_server()
    
    @tool
    def query_historical_prices_tool(start_date: str, end_date: str, hour: int = None) -> str:
        """
        Query historical electricity prices from PostgreSQL.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            hour: Optional hour (0-23) to filter specific hour
        
        Returns:
            JSON string with price data and statistics
        """
        result = server.query_historical_prices(start_date, end_date, hour)
        return json.dumps(result)
    
    @tool
    def get_price_statistics_tool(start_date: str, end_date: str) -> str:
        """
        Get aggregated price statistics for a date range including daily and hourly averages.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            JSON string with daily and hourly statistics
        """
        result = server.get_price_statistics(start_date, end_date)
        return json.dumps(result)
    
    @tool
    def find_cheapest_hours_tool(start_date: str, end_date: str, top_n: int = 5) -> str:
        """
        Find the cheapest hours in a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            top_n: Number of cheapest hours to return (default: 5)
        
        Returns:
            JSON string with cheapest hour slots
        """
        result = server.find_cheapest_hours(start_date, end_date, top_n)
        return json.dumps(result)
    
    return [
        query_historical_prices_tool,
        get_price_statistics_tool,
        find_cheapest_hours_tool,
    ]
