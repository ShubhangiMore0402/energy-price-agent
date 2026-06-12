import pandas as pd


def clean_price_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize data into a clean price table while preserving timestamps when available.
    """

    df = df.copy()

    keep_columns = [column for column in ["timestamp", "hour", "price_eur_mwh", "source"] if column in df.columns]
    df = df[keep_columns]

    df["price_eur_mwh"] = pd.to_numeric(df["price_eur_mwh"], errors="coerce")

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["date"] = df["timestamp"].dt.date

    df = df.dropna()

    return df