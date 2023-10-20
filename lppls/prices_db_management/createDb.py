import psycopg2

try:
    # Connect to Postgres server
    conn = psycopg2.connect(
        host="localhost",
        database="asset_prices",
        user="sornette",
        password="sornette",
        port="5432"
    )

    conn.autocommit = True

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TYPE asset_type AS ENUM ('ETF', 'STOCK');
    """)             

    # Create a table for stock prices
    cursor.execute("""
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
    """)

    print("Database created successfully")

except Exception as e:
    print(f"Error: {e}")

finally:
    if 'conn' in locals():
        cursor.close()
        conn.close()
