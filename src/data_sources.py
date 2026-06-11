import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests

# Support both module imports and direct execution
try:
    from .config import AWATTAR_API_URL, DEFAULT_TIMEOUT
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.config import AWATTAR_API_URL, DEFAULT_TIMEOUT


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