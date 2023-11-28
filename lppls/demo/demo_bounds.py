import sys

sys.path.append("/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls")
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/metrics"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/bubble_bounds"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/common"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/prices_db_management"
)

import pandas as pd
import psycopg2
import matplotlib.pyplot as plt
from peaks import Peaks
from lppls_dataclasses import BubbleType
from starts import Starts
from sornette import Sornette
from lppls_defaults import (
    LARGEST_WINDOW_SIZE,
    T1_STEP,
    MAX_SEARCHES,
    SMALLEST_WINDOW_SIZE,
    RECENT_VISIBLE_WINDOWS,
)
from lppls_dataclasses import Observation, ObservationSeries
from pop_dates import PopDates


def get_bubble_scores(sornette: Sornette, default_fitting_params, recent_windows):
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
    all_observations = ObservationSeries(
        [Observation(p, d) for d, p in zip(all_dates, all_actual_prices)]
    )

    _, drawdowns, _ = Peaks(all_observations, ticker).plot_peaks()
    first_eligible_date = all_dates.index(drawdowns[-1].date_ordinal)
    selected_actual_prices = all_actual_prices[first_eligible_date:]
    selected_dates = all_dates[first_eligible_date:]
    selected_observations = ObservationSeries(
        [Observation(p, d) for d, p in zip(selected_dates, selected_actual_prices)]
    )

    sornette_on_interval = Sornette(
        selected_observations,
        "BitcoinB",
        "./lppls/conf/demos2015_filter.json",
    )
    sornette_on_interval.plot_fit()

    expected_prices = sornette_on_interval.estimate_prices()

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

    # I want to see the start date on the entire interval, so I make another Sornette object
    sornette_on_interval = Sornette(
        all_observations, "BitcoinB", "./lppls/conf/demos2015_filter.json"
    )
    bubble_scores = get_bubble_scores(
        sornette_on_interval, default_fitting_params, RECENT_VISIBLE_WINDOWS
    )

    best_cluster = PopDates().compute_bubble_end_cluster(optimal_start, bubble_scores)
    sornette_on_interval.plot_bubble_scores(bubble_scores, ticker, optimal_start, best_cluster)

    plt.show(block=True)


if __name__ == "__main__":
    main()
