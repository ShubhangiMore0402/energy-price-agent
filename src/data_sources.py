import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Support both module imports and direct execution
try:
    from .config import AWATTAR_API_URL, DEFAULT_TIMEOUT, DATABASE_URL
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.config import AWATTAR_API_URL, DEFAULT_TIMEOUT, DATABASE_URL


def fetch_awattar_prices(date: str) -> pd.DataFrame:
    """
    Fetch German electricity market prices from aWATTar API for a selected date.

    Returns:
    timestamp | hour | price_eur_mwh | source
    """

    selected_date = pd.to_datetime(date).normalize()

    start = int(selected_date.timestamp() * 1000)
    end = int((selected_date + pd.Timedelta(days=1)).timestamp() * 1000)

    params = {
        "start": start,
        "end": end,
    }

    response = requests.get(
        AWATTAR_API_URL,
        params=params,
        timeout=DEFAULT_TIMEOUT
    )
    response.raise_for_status()

    payload = response.json()
    data = payload.get("data", [])

    if not data:
        raise ValueError(f"No aWATTar price data returned for {date}")

    rows = []

    for item in data:
        timestamp = pd.to_datetime(item["start_timestamp"], unit="ms")
        price = item["marketprice"]

        rows.append({
            "timestamp": timestamp,
            "hour": timestamp.hour,
            "price_eur_mwh": price,
            "source": "aWATTar",
        })

    df = pd.DataFrame(rows)

    # Validate that API response actually matches selected date
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    selected_date_only = selected_date.date()

    df = df[df["timestamp"].dt.date == selected_date_only]

    if df.empty:
        raise ValueError(
            f"aWATTar returned data, but no rows matched selected date {date}."
        )

    return df


def get_sample_prices() -> pd.DataFrame:
    """
    Fallback sample data for local/demo testing only.
    """

    data = {
        "timestamp": pd.date_range(
            start=pd.Timestamp.today().normalize(),
            periods=24,
            freq="h"
        ),
        "hour": list(range(24)),
        "price_eur_mwh": [
            82, 76, 70, 65, 61, 68, 90, 120,
            135, 118, 100, 92, 88, 85, 87, 95,
            110, 145, 160, 138, 120, 105, 96, 89
        ],
        "source": ["Sample"] * 24,
    }

    return pd.DataFrame(data)


def test_db_connection() -> bool:
    """
    Test PostgreSQL database connection.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✓ PostgreSQL connection successful!")
            return True
    except SQLAlchemyError as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during connection test: {e}")
        return False


def create_prices_table():
    """
    Create the electricity_prices table in PostgreSQL if it doesn't exist.
    """
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        with engine.connect() as connection:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS electricity_prices (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL UNIQUE,
                    hour INT NOT NULL,
                    price_eur_mwh FLOAT NOT NULL,
                    source VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            connection.commit()
            print("✓ Table 'electricity_prices' created/verified successfully!")
    except SQLAlchemyError as e:
        print(f"✗ Error creating table: {e}")
        raise


def fetch_historical_awattar_prices(months: int = 6) -> pd.DataFrame:
    """
    Fetch historical German electricity market prices from aWATTar API for the past N months.
    
    Args:
        months: Number of months of historical data to fetch (default: 6)
    
    Returns:
        pd.DataFrame: Combined historical price data
    """
    all_data = []
    end_date = pd.Timestamp.today().normalize()
    
    print(f"Fetching {months} months of historical aWATTar price data...")
    
    for i in range(months):
        # Calculate the date for each month
        current_date = end_date - pd.Timedelta(days=30 * i)
        date_str = current_date.strftime("%Y-%m-%d")
        
        try:
            print(f"  Fetching data for {date_str}...", end="")
            df = fetch_awattar_prices(date_str)
            all_data.append(df)
            print(" ✓")
        except ValueError as e:
            print(f" ✗ (No data: {str(e)[:50]}...)")
        except Exception as e:
            print(f" ✗ (Error: {str(e)[:50]}...)")
            continue
    
    if not all_data:
        raise ValueError("No historical price data could be fetched from aWATTar API")
    
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values("timestamp").reset_index(drop=True)
    
    print(f"\n✓ Successfully fetched {len(combined_df)} price records across {len(all_data)} days")
    return combined_df


def store_prices_in_db(df: pd.DataFrame):
    """
    Store electricity price data into PostgreSQL database with upsert logic.
    
    Args:
        df: DataFrame containing timestamp, hour, price_eur_mwh, source columns
    """
    if df.empty:
        print("✗ Cannot store empty DataFrame")
        return
    
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        
        # Convert timestamp to datetime if needed
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Use upsert (ON CONFLICT DO UPDATE) to handle duplicates
        with engine.connect() as connection:
            for idx, row in df.iterrows():
                query = text("""
                    INSERT INTO electricity_prices (timestamp, hour, price_eur_mwh, source)
                    VALUES (:timestamp, :hour, :price_eur_mwh, :source)
                    ON CONFLICT (timestamp) DO UPDATE SET
                        hour = EXCLUDED.hour,
                        price_eur_mwh = EXCLUDED.price_eur_mwh,
                        source = EXCLUDED.source
                """)
                connection.execute(query, {
                    "timestamp": row["timestamp"],
                    "hour": row["hour"],
                    "price_eur_mwh": row["price_eur_mwh"],
                    "source": row["source"]
                })
            connection.commit()
        
        print(f"✓ Successfully stored {len(df)} price records in PostgreSQL!")
        
    except Exception as e:
        print(f"✗ Error storing data in database: {e}")
        raise


def load_historical_data_to_db(months: int = 6):
    """
    Main function to test connection, create table, fetch historical data, and store in DB.
    
    Args:
        months: Number of months of historical data to fetch (default: 6)
    
    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 60)
    print("Loading Historical Energy Price Data to PostgreSQL")
    print("=" * 60)
    
    # Step 1: Test connection
    print("\n[1/4] Testing PostgreSQL connection...")
    if not test_db_connection():
        return False
    
    # Step 2: Create table
    print("\n[2/4] Creating/verifying database table...")
    try:
        create_prices_table()
    except Exception as e:
        print(f"Failed to create table: {e}")
        return False
    
    # Step 3: Fetch historical data
    print("\n[3/4] Fetching historical price data...")
    try:
        df = fetch_historical_awattar_prices(months=months)
    except Exception as e:
        print(f"Failed to fetch historical data: {e}")
        return False
    
    # Step 4: Store in database
    print("\n[4/4] Storing data in PostgreSQL...")
    try:
        store_prices_in_db(df)
    except Exception as e:
        print(f"Failed to store data: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ All steps completed successfully!")
    print("=" * 60)
    return True

