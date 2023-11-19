import yfinance as yf
import psycopg2
from datetime import datetime

try:
    # Connect to the database
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )

    cursor = conn.cursor()

    # Fetch data from Yahoo Finance
    pricing_history = yf.download(
        "VLO", start="2020-01-01", end=datetime.now().strftime("%Y-%m-%d")
    )

    # Insert the data into the database
    for index, row in pricing_history.iterrows():
        cursor.execute(
            """
            INSERT INTO pricing_history (date, ticker, name, open_price, high_price, low_price, close_price, volume)
            VALUES (%s, 'VLO', 'Valero Energy Corp', %s, %s, %s, %s, %s)
            ON CONFLICT (date, ticker)
            DO UPDATE SET open_price=EXCLUDED.open_price, high_price=EXCLUDED.high_price, low_price=EXCLUDED.low_price, close_price=EXCLUDED.close_price, volume=EXCLUDED.volume;
        """,
            (index, row["Open"], row["High"], row["Low"], row["Adj Close"], row["Volume"]),
        )

    conn.commit()
    print("Data inserted successfully")

except Exception as e:
    print(f"Error: {e}")

finally:
    if "conn" in locals():
        cursor.close()
        conn.close()
