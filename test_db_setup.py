import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_sources import (
    test_db_connection,
    create_prices_table,
    load_historical_data_to_db
)

if __name__ == "__main__":
    try:
        # Test 1: Just test connection
        print("\n" + "="*60)
        print("TESTING DATABASE CONNECTION")
        print("="*60)
        if test_db_connection():
            print("\n✓ Database connection is ready!")
        else:
            print("\n✗ Database connection failed!")
            print("\nPlease ensure:")
            print("  1. PostgreSQL is running on localhost:5432")
            print("  2. Database 'energy_prices' exists")
            print("  3. User 'shubhangimore' has access to the database")
            print("  4. Check .env file for correct credentials")
            sys.exit(1)
        
        # Test 2: Load 6 months of historical data
        print("\n")
        response = input("Do you want to load 6 months of historical data? (y/n): ").strip().lower()
        
        if response == 'y':
            success = load_historical_data_to_db(months=6)
            if success:
                print("\n✓ Historical data loaded successfully!")
                sys.exit(0)
            else:
                print("\n✗ Failed to load historical data")
                sys.exit(1)
        else:
            print("Skipped historical data loading.")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
