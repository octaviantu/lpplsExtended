import sys

sys.path.append("/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls")
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/metrics"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/prices_db_management"
)


import csv
import numpy as np
import pandas as pd
import psycopg2
from sornette import Sornette
from lppls_defaults import (
    LARGEST_WINDOW_SIZE,
    SMALLEST_WINDOW_SIZE,
    T1_STEP,
    T2_STEP,
    MAX_SEARCHES,
    T1_STEP_STRICT,
    SMALLEST_WINDOW_SIZE_STRICT,
    LARGEST_WINDOW_SIZE_STRICT,
    RECENT_VISIBLE_WINDOWS,
)
import argparse
from matplotlib import pyplot as plt
import os
from datetime import datetime
from lppls_defaults import BubbleType
from peaks import Peaks
import warnings
from pop_dates import PopDates
import bisect
from pop_dates import Cluster
from lppls_suggestions import LpplsSuggestions
from db_dataclasses import Suggestion, OrderType

# Convert warnings to exceptions
warnings.filterwarnings("error", category=RuntimeWarning)


BUBBLE_THRESHOLD = 0.25
# windows that are close to the end of the data, to see if there is a recent bubble
RECENT_RELEVANT_WINDOWS = 5
LIMIT_OF_MOST_TRADED_COMPANIES = 250
PLOTS_DIR = "plots/lppls"
PEAKS_DIR = PLOTS_DIR + "/peaks"
CSV_COLUMN_NAMES = [
    "Ticker",
    "Name",
    "Asset Type",
    "Bubble Type",
    "Max Confidence",
    "End times count",
    "End times",
    "Silhoutte",
]


def get_bubble_scores(sornette: Sornette, default_fitting_params, recent_windows):
    return sornette.compute_bubble_scores(
        workers=8,
        recent_windows=recent_windows,
        window_size=default_fitting_params["largest_window_size"],
        smallest_window_size=default_fitting_params["smallest_window_size"],
        t1_increment=default_fitting_params["t1_step"],
        t2_increment=T2_STEP,
        max_searches=MAX_SEARCHES,
    )


def is_in_bubble_state(times, prices, filter_type, filter_file, default_fitting_params):
    log_prices = np.log(prices)
    sornette = Sornette(np.array([times, log_prices]), filter_type, filter_file)

    bubble_scores = get_bubble_scores(sornette, default_fitting_params, RECENT_RELEVANT_WINDOWS)
    max_pos_conf = bubble_scores["pos_conf"].max()
    max_neg_conf = bubble_scores["neg_conf"].max()

    if max_pos_conf > BUBBLE_THRESHOLD:
        return BubbleType.POSITIVE, list(bubble_scores["pos_conf"]), sornette
    elif max_neg_conf > BUBBLE_THRESHOLD:
        return BubbleType.NEGATIVE, list(bubble_scores["neg_conf"]), sornette

    return None, 0, sornette


SPECIFIC_TICKERS = ["SMR"]
def plot_specific(cursor: psycopg2.extensions.cursor, default_fitting_params) -> None:
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()
    for ticker in SPECIFIC_TICKERS:
        query = f"SELECT date, close_price FROM pricing_history WHERE ticker='{ticker}' ORDER BY date ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        dates = [pd.Timestamp.toordinal(row[0]) for row in rows]
        prices = [row[1] for row in rows]

        bubble_type, _, sornette = is_in_bubble_state(
            dates, prices, "BitcoinB", "./lppls/conf/demos2015_filter.json", default_fitting_params
        )

        drawups, drawdowns, _ = Peaks(dates, prices, ticker).plot_peaks()

        start_time = sornette.compute_start_time(
            dates, prices, bubble_type, drawups if bubble_type == BubbleType.POSITIVE else drawdowns
        )
        bubble_scores = get_bubble_scores(sornette, default_fitting_params, RECENT_VISIBLE_WINDOWS)
        sornette.plot_bubble_scores(bubble_scores, ticker, start_time, Cluster())
        plt.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--specific", action="store_true", help="Plot only specific stocks")
    parser.add_argument("--type", type=str, help="Type of asset to consider ('stock' or 'etf')")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Apply smaller and more fitting windows",
        default=False,
    )

    args = parser.parse_args()

    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()

    default_fitting_params = {
        "t1_step": T1_STEP_STRICT if args.strict else T1_STEP,
        "smallest_window_size": SMALLEST_WINDOW_SIZE_STRICT
        if args.strict
        else SMALLEST_WINDOW_SIZE,
        "largest_window_size": LARGEST_WINDOW_SIZE_STRICT if args.strict else LARGEST_WINDOW_SIZE,
    }

    if args.specific:
        plot_specific(cursor, default_fitting_params)
        return

    stock_query = f"""SELECT ticker
                    FROM pricing_history
                    WHERE type = 'STOCK'
                    AND date = (SELECT MAX(date) FROM pricing_history WHERE type = 'STOCK')
                    ORDER BY volume DESC LIMIT {LIMIT_OF_MOST_TRADED_COMPANIES}"""
    etf_query = """SELECT ticker
                    FROM pricing_history
                    WHERE type = 'ETF'"""

    if args.type and args.type.lower() == "stock":
        sql_query = stock_query
    elif args.type and args.type.lower() == "etf":
        sql_query = etf_query
    else:
        sql_query = f"({stock_query}) UNION ({etf_query})"

    cursor.execute(sql_query)
    tickers = cursor.fetchall()
    positive_bubbles, negative_bubbles = [], []
    bubble_assets = []
    today_date = datetime.today().strftime("%Y-%m-%d")
    suggestions = []

    print(f"Will go through {len(tickers)} tickers.")
    for index, (ticker,) in enumerate(tickers):
        print(f"Now checking {ticker}, step {index} of {len(tickers)}")
        query = f"SELECT date, close_price FROM pricing_history WHERE ticker='{ticker}' ORDER BY date ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        dates = [pd.Timestamp.toordinal(row[0]) for row in rows]
        prices = [row[1] for row in rows]

        bubble_type, bubble_confidences, sornette = is_in_bubble_state(
            dates, prices, "BitcoinB", "./lppls/conf/demos2015_filter.json", default_fitting_params
        )

        if bubble_type:
            print(f"{ticker} meets criteria")
            cursor.execute(
                f"SELECT name, type FROM pricing_history WHERE ticker='{ticker}' LIMIT 1;"
            )
            name, asset_type = cursor.fetchone()

            drawups, drawdowns, peak_image_name = Peaks(dates, prices, ticker).plot_peaks()
            peak_file_name = f"{peak_image_name.replace(' ', '_').replace('on', '')}.png"

            if not os.path.exists(PEAKS_DIR):
                os.makedirs(PEAKS_DIR)
            peak_file_path = os.path.join(PEAKS_DIR, peak_file_name)
            plt.savefig(peak_file_path, dpi=300, bbox_inches="tight")

            if bubble_type == BubbleType.POSITIVE:
                positive_bubbles.append(ticker)
                dir_path = os.path.join(PLOTS_DIR, today_date, "positive")

            elif bubble_type == BubbleType.NEGATIVE:
                negative_bubbles.append(ticker)
                dir_path = os.path.join(PLOTS_DIR, today_date, "negative")

            start_time = sornette.compute_start_time(
                dates,
                prices,
                bubble_type,
                drawups if bubble_type == BubbleType.POSITIVE else drawdowns,
            )

            days_from_start = find_index_or_below(dates, dates[-1]) - find_index_or_below(
                dates, start_time.date_ordinal
            )

            plotted_time = max(RECENT_VISIBLE_WINDOWS, days_from_start)
            bubble_scores = get_bubble_scores(sornette, default_fitting_params, plotted_time)

            best_end_cluster = PopDates().compute_bubble_end_cluster(start_time, bubble_scores)
            sornette.plot_bubble_scores(bubble_scores, ticker, start_time, best_end_cluster)

            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            # Save the figure
            bubble_score_file_name = f"{ticker}.png"
            bubble_score_file_path = os.path.join(dir_path, bubble_score_file_name)
            plt.savefig(bubble_score_file_path, dpi=300, bbox_inches="tight")

            bubble_assets.append(
                {
                    CSV_COLUMN_NAMES[0]: ticker,
                    CSV_COLUMN_NAMES[1]: name,
                    CSV_COLUMN_NAMES[2]: asset_type,
                    CSV_COLUMN_NAMES[3]: bubble_type.value,
                    CSV_COLUMN_NAMES[4]: f"{max(bubble_confidences):.2f}",
                    CSV_COLUMN_NAMES[5]: best_end_cluster.pop_dates_count(),
                    CSV_COLUMN_NAMES[6]: best_end_cluster.displayCluster(),
                    CSV_COLUMN_NAMES[7]: best_end_cluster.silhouette,
                }
            )

            # Make trading suggestions to the databse used for backtesting.
            pop_dates_range = best_end_cluster.give_pop_dates_range()
            order_type = OrderType.SELL if bubble_type == BubbleType.POSITIVE else OrderType.BUY

            if pop_dates_range:
                suggestions.append(Suggestion(
                    order_type=order_type,
                    ticker=ticker,
                    confidence=bubble_confidences[-1], # the confidence for the last date
                    price=prices[-1],
                    open_date=dates[-1],
                    pop_dates_range=pop_dates_range,
                ))

    LpplsSuggestions().write_suggestions(suggestions)

    csv_file_path = os.path.join(PLOTS_DIR, today_date, "bubble_assets.csv")
    with open(csv_file_path, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMN_NAMES)
        writer.writeheader()
        for asset in bubble_assets:
            writer.writerow(asset)


def find_index_or_below(lst, value):
    index = bisect.bisect_left(lst, value)
    if index == len(lst) or lst[index] != value:
        return index - 1
    else:
        return index


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # TODO(octaviant) - fix because this actually does not catch all exceptions
        sys.exit(1)  # Exit with a non-zero code to indicate failure


# To show only a specific set of tickers:
# python demoSP.py --specific

# To display only stocks:
# python demoSP.py --type stocks

# To display only etfs:
# python demoSP.py --type etf

# To Use more windows for fitting:
# python demoSP.py --strict
