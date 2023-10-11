import sys

sys.path.append("/Users/octaviantuchila/Documents/MonteCarlo/Sornette/lppls_python_updated/lppls")
import numpy as np
import pandas as pd
import psycopg2
from datetime import date
import matplotlib.pyplot as plt
from sornette import Sornette
from lppls_defaults import LARGEST_WINDOW_SIZE, SMALLEST_WINDOW_SIZE, T1_STEP, T2_STEP, MAX_SEARCHES


def execute_lppls_logic(data_filtered, filter_type, filter_file):
    # Convert time to ordinal
    time_filtered = [pd.Timestamp.toordinal(dt) for dt in data_filtered["Date"]]

    # Log price
    price_filtered = np.log(data_filtered["Adj Close"].values)

    # Observations
    observations_filtered = np.array([time_filtered, price_filtered])

    # LPPLS Model for filtered data
    sornette = Sornette(observations_filtered, filter_type, filter_file)
    sornette.fit(MAX_SEARCHES)
    sornette.plot_fit()

    res_filtered = sornette.mp_compute_t1_fits(
        workers=8,
        window_size=LARGEST_WINDOW_SIZE,
        smallest_window_size=SMALLEST_WINDOW_SIZE,
        outer_increment=T1_STEP,
        inner_increment=T2_STEP,
        max_searches=MAX_SEARCHES,
    )
    sornette.plot_bubble_scores(res_filtered)


def main():
    # Fetch VLO data from the database
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()
    query = "SELECT date, close_price FROM stock_data WHERE ticker='VLO' ORDER BY date ASC;"
    cursor.execute(query)
    rows = cursor.fetchall()
    data = pd.DataFrame(rows, columns=["Date", "Adj Close"])

    # Filter data up to June 1, 2022
    filter_date = date(2022, 6, 1)
    data_filtered = data[data["Date"] <= filter_date]

    # First run
    # execute_lppls_logic(data_filtered)

    # Second run with different config
    execute_lppls_logic(data_filtered, "Shanghai", "./lppls/conf/shanghai_filter2.json")
    # execute_lppls_logic(data_filtered, 'BitcoinB', './lppls/conf/bitcoin_filter2019B.json')

    plt.show()


if __name__ == "__main__":
    main()
