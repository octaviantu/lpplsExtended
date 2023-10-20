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
LIMIT_OF_MOST_TRADED_COMPANIES = 200


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
    for ticker in SPECIFIC_TICKERS:
        query = f"SELECT date, close_price FROM pricing_history WHERE ticker='{ticker}' ORDER BY date ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        closing_prices = pd.DataFrame(rows, columns=["Date", "Adj Close"])
        plot_bubble_fits(closing_prices, 'BitcoinB', './lppls/conf/demos2015_filter.json', ticker)

    plt.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--display", action="store_true", help="Display bubble scores plot for each company")
    parser.add_argument("--specific", action="store_true", help="Plot only specific stocks")
    parser.add_argument("--type", type=str, help="Type of asset to consider ('stock' or 'etf')")

    args = parser.parse_args()

    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()

    if args.specific:
        plot_specific(cursor)
        return

    stock_query = f"""SELECT ticker
                    FROM pricing_history
                    WHERE type = 'STOCK'
                    AND date = (SELECT MAX(date) FROM pricing_history WHERE type = 'STOCK')
                    ORDER BY volume DESC LIMIT {LIMIT_OF_MOST_TRADED_COMPANIES}"""
    etf_query = """SELECT ticker
                    FROM pricing_history
                    WHERE type = 'ETF'"""

    if args.type and args.type.lower() == 'stock':
        sql_query = stock_query
    elif args.type and args.type.lower() == 'etf':
        sql_query = etf_query
    else:
        sql_query = f"({stock_query}) UNION ({etf_query})"


    cursor.execute(sql_query)
    tickers = cursor.fetchall()
    tickers_with_criteria = []

    print(f'Will go through {len(tickers)} tickers.')
    for index, ticker in enumerate(tickers):

        print(f'Now checking {ticker}, step {index} of {len(tickers)}')
        query = f"SELECT date, close_price FROM pricing_history WHERE ticker='{ticker}' ORDER BY date ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        closing_prices = pd.DataFrame(rows, columns=["Date", "Adj Close"])

        if is_in_bubble_state(closing_prices, 'BitcoinB', './lppls/conf/demos2015_filter.json'):
            print(f'{ticker} meets criteria')
            tickers_with_criteria.append(ticker)
            if args.display:
                plot_bubble_fits(closing_prices, 'BitcoinB', './lppls/conf/demos2015_filter.json', ticker)            

    print("Stocks that meet the criteria:", tickers_with_criteria)

    if args.display:
        plt.show()



if __name__ == "__main__":
    main()


# To display the plots:
# python demoSP.py --display

# To show only a specific set of tickers:
# python demoSP.py --specific

# To display only stocks:
# python demoSP.py --display --type stocks

# To display only etfs:
# python demoSP.py --display --type etf