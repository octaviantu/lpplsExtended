import sys
sys.path.append("/Users/octaviantuchila/Documents/MonteCarlo/Sornette/lppls_python_updated/lppls")
sys.path.append("/Users/octaviantuchila/Documents/MonteCarlo/Sornette/lppls_python_updated/lppls/metrics")

import numpy as np
import pandas as pd
import psycopg2
from sornette import Sornette
from lppls_defaults import LARGEST_WINDOW_SIZE, SMALLEST_WINDOW_SIZE, T1_STEP, T2_STEP, MAX_SEARCHES
import argparse
from matplotlib import pyplot as plt


BUBBLE_THRESHOLD = 0.25
# windows that are close to the end of the data, to see if there is a recent bubble
RECENT_RELEVANT_WINDOWS = 5
RECENT_VISIBLE_WINDOWS = 200
LIMIT_OF_LARGEST_COMPANIES = 200


def is_in_bubble_state(closing_prices, filter_type, filter_file):
    times = [pd.Timestamp.toordinal(dt) for dt in closing_prices["Date"]]
    prices = np.log(closing_prices["Adj Close"].values)

    observations_filtered = np.array([times, prices])
    sornette = Sornette(observations_filtered, filter_type, filter_file)

    fits = sornette.parallel_compute_t2_recent_fits(
        workers=8,
        recent_windows=RECENT_RELEVANT_WINDOWS,
        window_size=LARGEST_WINDOW_SIZE,
        smallest_window_size=SMALLEST_WINDOW_SIZE,
        t1_increment=T1_STEP,
        t2_increment=T2_STEP,
        max_searches=MAX_SEARCHES,
    )
    bubble_scores = sornette.bubble_scores.compute_bubble_scores(fits)
    for _, row in bubble_scores.iterrows():
        if row["pos_conf"] > BUBBLE_THRESHOLD or row["neg_conf"] > BUBBLE_THRESHOLD:
            return True

    return False



def plot_bubble_fits(closing_prices, filter_type, filter_file, ticker):
    times = [pd.Timestamp.toordinal(dt) for dt in closing_prices["Date"]]
    prices = np.log(closing_prices["Adj Close"].values)

    observations_filtered = np.array([times, prices])
    sornette = Sornette(observations_filtered, filter_type, filter_file)

    fits = sornette.parallel_compute_t2_recent_fits(
        workers=8,
        recent_windows=RECENT_VISIBLE_WINDOWS,
        window_size=LARGEST_WINDOW_SIZE,
        smallest_window_size=SMALLEST_WINDOW_SIZE,
        t1_increment=T1_STEP,
        t2_increment=T2_STEP,
        max_searches=MAX_SEARCHES,
    )
    sornette.plot_bubble_scores(fits, ticker)



SPECIFIC_TICKERS = ['CSCO', 'UNP', 'TJX', 'ETN', 'FI', 'MPC', 'ROP', 'AJG', 'AFL', 'GIS', 'CEG', 'BIIB']
def plot_specific(cursor: psycopg2.extensions.cursor) -> None:
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()
    for symbol in SPECIFIC_TICKERS:
        query = f"SELECT date, close_price FROM stock_data WHERE ticker='{symbol}' ORDER BY date ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        closing_prices = pd.DataFrame(rows, columns=["Date", "Adj Close"])
        plot_bubble_fits(closing_prices, 'BitcoinB', './lppls/conf/demos2015_filter.json', symbol)

    plt.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--display", action="store_true", help="Display bubble scores plot for each company")
    parser.add_argument("--specific", action="store_true", help="Plot only specific stocks")
    args = parser.parse_args()

    
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()
    if args.specific:
        plot_specific(cursor)
        return

    cursor.execute(f"SELECT symbol, company FROM sp500_components ORDER BY CAST(portfolio_percent as FLOAT) DESC LIMIT {LIMIT_OF_LARGEST_COMPANIES}")
    symbols = cursor.fetchall()
    symbols_with_criteria = []

    for symbol, _ in symbols:
        query = f"SELECT date, close_price FROM stock_data WHERE ticker='{symbol}' ORDER BY date ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        closing_prices = pd.DataFrame(rows, columns=["Date", "Adj Close"])

        if is_in_bubble_state(closing_prices, 'BitcoinB', './lppls/conf/demos2015_filter.json'):
            symbols_with_criteria.append(symbol)
            if args.display:
                plot_bubble_fits(closing_prices, 'BitcoinB', './lppls/conf/demos2015_filter.json', symbol)            

    print("Stocks that meet the criteria:", symbols_with_criteria)

    if args.display:
        plt.show()



if __name__ == "__main__":
    main()


# To display the plots:
# python demoSP.py --display

# To show only a specific set of tickers:
# python demoSP.py --specific