import sys

sys.path.append("/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls")
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/metrics"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/bubble_bounds"
)

import pandas as pd
import psycopg2
import matplotlib.pyplot as plt
from peaks import Peaks
from lppls_defaults import BubbleType
from bounds import Bounds

def main():
    ticker = "BIV"
    # Fetch VLO data from the database
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()
    query = f"SELECT date, close_price FROM pricing_history WHERE ticker='{ticker}' ORDER BY date ASC;"
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Separate the dates and prices into two lists
    dates = [pd.Timestamp.toordinal(row[0]) for row in rows]
    prices = [row[1] for row in rows]

    _, drawdowns, _ = Peaks(dates, prices, ticker).plot_peaks()

    bounds = Bounds()
    bounds.compute_start_time(dates, prices, prices, BubbleType.NEGATIVE, drawdowns)

    plt.show()


if __name__ == "__main__":
    main()
