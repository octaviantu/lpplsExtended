import sys
import csv

sys.path.append("/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls")
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/metrics"
)

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
)
import argparse
from matplotlib import pyplot as plt
from enum import Enum
import os
from datetime import datetime


BUBBLE_THRESHOLD = 0.25
# windows that are close to the end of the data, to see if there is a recent bubble
RECENT_RELEVANT_WINDOWS = 5
RECENT_VISIBLE_WINDOWS = 200
LIMIT_OF_MOST_TRADED_COMPANIES = 200
PLOTS_DIR = 'plots'
CSV_COLUMN_NAMES = ["Ticker", "Name", "Asset Type", "Bubble Type", "Max Confidence"]


class BubbleType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


def is_in_bubble_state(closing_prices, filter_type, filter_file, default_fitting_params):
    times = [pd.Timestamp.toordinal(dt) for dt in closing_prices["Date"]]
    prices = np.log(closing_prices["Adj Close"].values)

    observations_filtered = np.array([times, prices])
    sornette = Sornette(observations_filtered, filter_type, filter_file)

    fits = sornette.parallel_compute_t2_recent_fits(
        workers=8,
        recent_windows=RECENT_RELEVANT_WINDOWS,
        window_size=default_fitting_params["largest_window_size"],
        smallest_window_size=default_fitting_params["smallest_window_size"],
        t1_increment=default_fitting_params["t1_step"],
        t2_increment=T2_STEP,
        max_searches=MAX_SEARCHES,
    )
    bubble_scores = sornette.bubble_scores.compute_bubble_scores(fits)
    max_pos_conf = bubble_scores["pos_conf"].max()
    max_neg_conf = bubble_scores["neg_conf"].max()

    if max_pos_conf > BUBBLE_THRESHOLD:
        return BubbleType.POSITIVE, max_pos_conf
    elif max_neg_conf > BUBBLE_THRESHOLD:
        return BubbleType.NEGATIVE, max_neg_conf

    return None, 0


def plot_bubble_fits(closing_prices, filter_type, filter_file, ticker, default_fitting_params):
    times = [pd.Timestamp.toordinal(dt) for dt in closing_prices["Date"]]
    prices = np.log(closing_prices["Adj Close"].values)

    observations_filtered = np.array([times, prices])
    sornette = Sornette(observations_filtered, filter_type, filter_file)

    fits = sornette.parallel_compute_t2_recent_fits(
        workers=8,
        recent_windows=RECENT_VISIBLE_WINDOWS,
        window_size=default_fitting_params["largest_window_size"],
        smallest_window_size=default_fitting_params["smallest_window_size"],
        t1_increment=default_fitting_params["t1_step"],
        t2_increment=T2_STEP,
        max_searches=MAX_SEARCHES,
    )
    sornette.plot_bubble_scores(fits, ticker)


SPECIFIC_TICKERS = ["AGG", "EMCR", "ET", "AAPL"]
def plot_specific(cursor: psycopg2.extensions.cursor, default_fitting_params) -> None:
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()
    for ticker in SPECIFIC_TICKERS:
        query = f"SELECT date, close_price FROM pricing_history WHERE ticker='{ticker}' ORDER BY date ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        closing_prices = pd.DataFrame(rows, columns=["Date", "Adj Close"])
        plot_bubble_fits(
            closing_prices,
            "BitcoinB",
            "./lppls/conf/demos2015_filter.json",
            ticker,
            default_fitting_params,
        )

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

    print(f"Will go through {len(tickers)} tickers.")
    for index, (ticker,) in enumerate(tickers):
        print(f"Now checking {ticker}, step {index} of {len(tickers)}")
        query = f"SELECT date, close_price FROM pricing_history WHERE ticker='{ticker}' ORDER BY date ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        closing_prices = pd.DataFrame(rows, columns=["Date", "Adj Close"])

        bubble_state, max_conf = is_in_bubble_state(
            closing_prices, "BitcoinB", "./lppls/conf/demos2015_filter.json", default_fitting_params
        )

        if bubble_state:
            print(f"{ticker} meets criteria")
            cursor.execute(f"SELECT name, type FROM pricing_history WHERE ticker='{ticker}' LIMIT 1;")
            name, asset_type = cursor.fetchone()
            bubble_assets.append({
                CSV_COLUMN_NAMES[0]: ticker,
                CSV_COLUMN_NAMES[1]: name,
                CSV_COLUMN_NAMES[2]: asset_type,
                CSV_COLUMN_NAMES[3]: bubble_state.value,
                CSV_COLUMN_NAMES[4]: f'{max_conf:.2f}'
            })

            # Define the directory path based on the bubble state
            today_date = datetime.today().strftime('%Y-%m-%d')

            if bubble_state == BubbleType.POSITIVE:
                positive_bubbles.append(ticker)
                dir_path = os.path.join(PLOTS_DIR, today_date, 'positive')

            elif bubble_state == BubbleType.NEGATIVE:
                negative_bubbles.append(ticker)
                dir_path = os.path.join(PLOTS_DIR, today_date, 'negative')

            plot_bubble_fits(
                closing_prices,
                "BitcoinB",
                "./lppls/conf/demos2015_filter.json",
                ticker,
                default_fitting_params,
            )

            # Create the directory if it doesn't exist
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            # Save the figure
            file_name = f"{ticker}.png"
            file_path = os.path.join(dir_path, file_name)
            plt.savefig(file_path, dpi=300, bbox_inches='tight')


    csv_file_path = os.path.join(PLOTS_DIR, today_date, 'bubble_assets.csv')
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMN_NAMES)
        writer.writeheader()
        for asset in bubble_assets:
            writer.writerow(asset)

    print("Positive bubbles: ", positive_bubbles)
    print("Negative bubbles: ", negative_bubbles)


if __name__ == "__main__":
    main()


# To show only a specific set of tickers:
# python demoSP.py --specific

# To display only stocks:
# python demoSP.py --type stocks

# To display only etfs:
# python demoSP.py --type etf

# To Use more windows for fitting:
# python demoSP.py --strict
