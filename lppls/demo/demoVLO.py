import sys
sys.path.append('/Users/octaviantuchila/Documents/MonteCarlo/Sornette/lppls/lppls')
from lppls import LPPLS
import numpy as np
import pandas as pd
import psycopg2
from datetime import datetime, date
import matplotlib.pyplot as plt


def main():
    # Fetch VLO data from the database
    conn = psycopg2.connect(
        host="localhost",
        database="asset_prices",
        user="sornette",
        password="sornette",
        port="5432"
    )
    cursor = conn.cursor()
    query = "SELECT date, close_price FROM stock_data WHERE ticker='VLO' ORDER BY date ASC;"
    cursor.execute(query)
    rows = cursor.fetchall()
    data = pd.DataFrame(rows, columns=['Date', 'Adj Close'])

    # Filter data up to June 1, 2022
    filter_date = date(2022, 6, 1)

    data_filtered = data[data['Date'] <= filter_date]

    # Convert time to ordinal
    time_filtered = [pd.Timestamp.toordinal(dt) for dt in data_filtered['Date']]

    # Log price
    price_filtered = np.log(data_filtered['Adj Close'].values)

    # Observations
    observations_filtered = np.array([time_filtered, price_filtered])

    # LPPLS Model for filtered data
    MAX_SEARCHES = 25
    lppls_model_filtered = LPPLS(observations=observations_filtered)
    lppls_model_filtered.fit(MAX_SEARCHES)
    lppls_model_filtered.plot_fit()

    res_filtered = lppls_model_filtered.mp_compute_nested_fits(
        workers=8,
        window_size=120, 
        smallest_window_size=30, 
        outer_increment=1, 
        inner_increment=5, 
        max_searches=25
    )
    lppls_model_filtered.plot_confidence_indicators(res_filtered)
    plt.show()



if __name__ == '__main__':
    main()
