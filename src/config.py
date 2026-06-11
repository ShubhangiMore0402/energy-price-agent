import os
from dotenv import load_dotenv

load_dotenv()

AWATTAR_API_URL = "https://api.awattar.de/v1/marketdata"
DEFAULT_TIMEOUT = 30
DEFAULT_SOURCE = "aWATTar"

# PostgreSQL Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "energy_prices")
DB_USER = os.getenv("DB_USER", "shubhangimore")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Database connection string
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"