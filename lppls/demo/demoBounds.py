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
from starts import Starts
import numpy as np
from sornette import Sornette
from lppls_defaults import (
    LARGEST_WINDOW_SIZE,
    T1_STEP,
    MAX_SEARCHES,
    SMALLEST_WINDOW_SIZE,
    RECENT_VISIBLE_WINDOWS,
)


def get_fits(sornette: Sornette, default_fitting_params, recent_windows):
    return sornette.compute_bubble_scores(
        workers=8,
        recent_windows=recent_windows,
        window_size=default_fitting_params["largest_window_size"],
        smallest_window_size=default_fitting_params["smallest_window_size"],
        t1_increment=5,
        t2_increment=2,
        max_searches=MAX_SEARCHES,
    )


def main():
    ticker = "BIV"
    # Fetch VLO data from the database
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()
    query = (
        f"SELECT date, close_price FROM pricing_history WHERE ticker='{ticker}' ORDER BY date ASC;"
    )
    cursor.execute(query)
    rows = cursor.fetchall()

    # Separate the dates and prices into two lists
    all_dates = [pd.Timestamp.toordinal(row[0]) for row in rows]
    all_actual_prices = [row[1] for row in rows]

    _, drawdowns, _ = Peaks(all_dates, all_actual_prices, ticker).plot_peaks()
    first_eligible_date = all_dates.index(drawdowns[-1].date_ordinal)
    selected_dates = all_dates[first_eligible_date:]
    selected_actual_prices = all_actual_prices[first_eligible_date:]
    selected_log_prices = np.log(selected_actual_prices)

    sornette_on_interval = Sornette(
        np.array([selected_dates, selected_log_prices]),
        "BitcoinB",
        "./lppls/conf/demos2015_filter.json",
    )
    sornette_on_interval.plot_fit()

    expected_prices = [np.exp(p) for p in sornette_on_interval.estimate_prices()]

    default_fitting_params = {
        "t1_step": T1_STEP,
        "smallest_window_size": SMALLEST_WINDOW_SIZE,
        "largest_window_size": LARGEST_WINDOW_SIZE,
    }

    starts = Starts()
    starts.plot_all_fit_measures(selected_actual_prices, expected_prices, selected_dates)
    optimal_start = starts.compute_start_time(
        selected_dates[: len(selected_dates) - SMALLEST_WINDOW_SIZE],
        selected_actual_prices,
        expected_prices,
        BubbleType.NEGATIVE,
        drawdowns,
    )

    # I want to see the start date on the entire interval, so I make another Sornettee object
    # TODO(octaviant) - creating a new Sornette object is complicated; simplify
    all_log_prices = np.log(all_actual_prices)
    sornette_on_interval = Sornette(
        np.array([all_dates, all_log_prices]), "BitcoinB", "./lppls/conf/demos2015_filter.json"
    )
    fits = get_fits(sornette_on_interval, default_fitting_params, RECENT_VISIBLE_WINDOWS)
    sornette_on_interval.plot_bubble_scores(fits, ticker, optimal_start)

    plt.show(block=True)


if __name__ == "__main__":
    main()
