import psycopg2
from prices_db_management.db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

try:
    # Connect to Postgres server
    conn = psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
    )

    conn.autocommit = True

    cursor = conn.cursor()

    cursor.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'asset_type') THEN
                CREATE TYPE asset_type AS ENUM ('ETF', 'STOCK', 'INDEX');
            END IF;
        END
        $$;
        """
    )


    # Create a table for stock prices
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pricing_history (
            date DATE,
            ticker VARCHAR(10),
            type asset_type,
            name TEXT,
            open_price FLOAT,
            high_price FLOAT,
            low_price FLOAT,
            close_price FLOAT,
            volume BIGINT,
            PRIMARY KEY (date, ticker, type)
        );
    """
    )

except Exception as e:
    print(f"Error: {e}")

finally:
    if "conn" in locals():
        cursor.close()
        conn.close()
