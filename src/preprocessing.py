import pandas as pd


def clean_price_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize data into the format:
    hour | price_eur_mwh
    """

    df = df.copy()

    # Example expected final structure
    df = df[["hour", "price_eur_mwh"]]

    df["price_eur_mwh"] = pd.to_numeric(df["price_eur_mwh"], errors="coerce")
    df = df.dropna()

    return df