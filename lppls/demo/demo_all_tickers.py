import sys

sys.path.append("/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls")
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/bubble_bounds"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/common"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/metrics"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/prices_db_management"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/previous_performance"
)


import csv
import psycopg2
from sornette import Sornette
from lppls_defaults import (
    LARGEST_WINDOW_SIZE,
    SMALLEST_WINDOW_SIZE,
    T1_STEP,
    T2_STEP,
    MAX_SEARCHES,
    OPTIMIZE_T1_STEP,
    RECENT_VISIBLE_WINDOWS
)
import argparse
from matplotlib import pyplot as plt
import os
from lppls_dataclasses import BubbleScore, BubbleType, Observation, ObservationSeries
from peaks import Peaks
import warnings
from pop_dates import PopDates
from lppls_suggestions import LpplsSuggestions
from db_dataclasses import Suggestion, OrderType
from typechecking import TypeCheckBase
from date_utils import DateUtils as du
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from typing import List
import cProfile

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

DEFAULT_BACKTEST_DAYS_BACK_LPPLS = 40


class AllTickers(TypeCheckBase):

    def get_connection(self):
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
        )

    def get_bubble_scores(self, sornette: Sornette, recent_windows: int, t1_step: int) -> List[BubbleScore]:
        return sornette.compute_bubble_scores(
            workers=8,
            recent_windows=recent_windows,
            window_size=LARGEST_WINDOW_SIZE,
            smallest_window_size=SMALLEST_WINDOW_SIZE,
            t1_increment=t1_step,
            t2_increment=T2_STEP,
            max_searches=MAX_SEARCHES,
        )

    def is_in_bubble_state(
        self,
        observations: ObservationSeries,
        filter_type: str,
        filter_file: str,
        should_optimize: bool,
    ) -> tuple[BubbleType | None, List[float], Sornette]:
            
        sornette = Sornette(observations, filter_type, filter_file, should_optimize)

        relevant_windows = 1 if should_optimize else RECENT_RELEVANT_WINDOWS
        t1_step = T1_STEP if should_optimize else OPTIMIZE_T1_STEP
        bubble_scores = self.get_bubble_scores(sornette, relevant_windows, t1_step)
        pos_conf = [bs.pos_conf for bs in bubble_scores]
        neg_conf = [bs.neg_conf for bs in bubble_scores]

        if max(pos_conf) > BUBBLE_THRESHOLD:
            return BubbleType.POSITIVE, pos_conf, sornette
        elif max(neg_conf) > BUBBLE_THRESHOLD:
            return BubbleType.NEGATIVE, neg_conf, sornette

        return None, [0.0], sornette

    def plot_specific(self, test_date: str) -> None:
        SPECIFIC_TICKERS = ["^GDAXI"]
        conn = self.get_connection()
        cursor = conn.cursor()
        for ticker in SPECIFIC_TICKERS:
            # Never select today - we run this before the market opens
            query = f"SELECT date, close_price FROM pricing_history WHERE ticker='{ticker}' AND date < '{test_date}' ORDER BY date ASC;"
            cursor.execute(query)
            rows = cursor.fetchall()
            observations = ObservationSeries(
                [Observation(price=row[1], date_ordinal=row[0].toordinal()) for row in rows]
            )

            bubble_type, _, sornette = self.is_in_bubble_state(
                observations,
                "BitcoinB",
                "./lppls/conf/demos2015_filter.json",
                should_optimize=True,
            )
            if not bubble_type:
                continue

            drawups, drawdowns, _ = Peaks(observations, ticker).plot_peaks(test_date)

            bubble_start = sornette.compute_start_time(
                observations,
                bubble_type,
                drawups if bubble_type == BubbleType.POSITIVE else drawdowns,
            )
            sornette.plot_fit(bubble_start)
            bubble_scores = self.get_bubble_scores(sornette, 50, T1_STEP)
            best_end_cluster = PopDates().compute_bubble_end_cluster(
                bubble_start, bubble_scores, test_date
            )

            sornette.plot_bubble_scores(bubble_scores, ticker, bubble_start, best_end_cluster)

            sornette.plot_rejection_reasons(bubble_scores, ticker)
        plt.show(block=True)

    def discover_daily(self, test_date: str, should_optimize=False) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()

        stock_query = f"""SELECT ticker
                        FROM pricing_history
                        WHERE type = 'STOCK'
                        AND date = (SELECT MAX(date) FROM pricing_history WHERE type = 'STOCK')
                        ORDER BY volume DESC LIMIT {LIMIT_OF_MOST_TRADED_COMPANIES}"""
        etf_query = """SELECT ticker
                        FROM pricing_history
                        WHERE type = 'ETF'"""
        index_query = """SELECT ticker
                        FROM pricing_history
                        WHERE type = 'INDEX'"""
        sql_query = f"({stock_query}) UNION ({etf_query}) UNION ({index_query})"

        cursor.execute(sql_query)
        tickers = cursor.fetchall()
        positive_bubbles, negative_bubbles = [], []
        bubble_assets = []
        suggestions = []

        daily_plots_dir_path = os.path.join(PLOTS_DIR, test_date)
        if not os.path.exists(daily_plots_dir_path):
            os.makedirs(daily_plots_dir_path)

        print(f"Will go through {len(tickers)} tickers.")
        for index, (ticker,) in enumerate(tickers):
            print(f"Now checking {ticker}, step {index} of {len(tickers)}")

            # Never select today - we run this before the market opens
            query = f"SELECT date, close_price FROM pricing_history WHERE ticker='{ticker}' AND date < '{test_date}' ORDER BY date ASC;"
            cursor.execute(query)
            rows = cursor.fetchall()
            observations = ObservationSeries(
                [Observation(price=row[1], date_ordinal=row[0].toordinal()) for row in rows]
            )

            if len(observations) < LARGEST_WINDOW_SIZE:
                print(f"Skipping {ticker} because it has too few observations.")
                continue

            print(
                f"the last observation is: {du.ordinal_to_date(observations[-1].date_ordinal)}, {observations[-1].price}"
            )

            bubble_type, bubble_confidences, sornette = self.is_in_bubble_state(
                observations, "BitcoinB", "./lppls/conf/demos2015_filter.json", should_optimize
            )

            if not bubble_type:
                continue
    
            print(f"{ticker} meets criteria")
            cursor.execute(
                f"SELECT name, type FROM pricing_history WHERE ticker='{ticker}' LIMIT 1;"
            )
            name, asset_type = cursor.fetchone()

            drawups, drawdowns, peak_image_name = Peaks(observations, ticker).plot_peaks(
                test_date
            )
            peak_file_name = f"{peak_image_name.replace(' ', '_').replace('on', '')}.png"

            if not os.path.exists(PEAKS_DIR):
                os.makedirs(PEAKS_DIR)
            peak_file_path = os.path.join(PEAKS_DIR, peak_file_name)
            plt.savefig(peak_file_path, dpi=300, bbox_inches="tight")

            if bubble_type == BubbleType.POSITIVE:
                positive_bubbles.append(ticker)
                bubble_dir_path = os.path.join(daily_plots_dir_path, "positive")
            elif bubble_type == BubbleType.NEGATIVE:
                negative_bubbles.append(ticker)
                bubble_dir_path = os.path.join(daily_plots_dir_path, "negative")

            start_time = sornette.compute_start_time(
                observations,
                bubble_type,
                drawups if bubble_type == BubbleType.POSITIVE else drawdowns,
            )

            days_from_start = len(
                observations.filter_between_date_ordinals(
                    start_date_ordinal=start_time.date_ordinal
                )
            )

            recent_visible_windows: int = (
                RECENT_VISIBLE_WINDOWS // 2 if should_optimize else RECENT_VISIBLE_WINDOWS
            )
            plotted_time = max(recent_visible_windows, days_from_start)
            bubble_scores = self.get_bubble_scores(sornette, plotted_time, T1_STEP)

            best_end_cluster = PopDates().compute_bubble_end_cluster(
                start_time, bubble_scores, test_date
            )
            sornette.plot_bubble_scores(bubble_scores, ticker, start_time, best_end_cluster)

            if not os.path.exists(bubble_dir_path):
                os.makedirs(bubble_dir_path)

            # Save the figure
            bubble_score_file_name = f"{ticker}.png"
            bubble_score_file_path = os.path.join(bubble_dir_path, bubble_score_file_name)
            plt.savefig(bubble_score_file_path, dpi=300, bbox_inches="tight")
            plt.close('all')

            if not should_optimize:
                rejections_file_name = f"{ticker}-rejections-breakdown.png"
                rejected_file_path = os.path.join(bubble_dir_path, rejections_file_name)
                sornette.plot_rejection_reasons(bubble_scores, ticker)
                plt.savefig(rejected_file_path, dpi=300, bbox_inches="tight")
                plt.close('all')

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
            pop_dates_range = best_end_cluster.give_pop_dates_range(test_date)
            order_type = OrderType.SELL if bubble_type == BubbleType.POSITIVE else OrderType.BUY

            if pop_dates_range:
                suggestions.append(
                    Suggestion(
                        order_type=order_type,
                        ticker=ticker,
                        confidence=bubble_confidences[-1],  # the confidence for the last date
                        price=observations[-1].price,
                        open_date=observations[-1].date_ordinal,
                        pop_dates_range=pop_dates_range,
                    )
                )

        LpplsSuggestions().write_suggestions(suggestions)

        csv_file_path = os.path.join(daily_plots_dir_path, "bubble_assets.csv")
        with open(csv_file_path, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMN_NAMES)
            writer.writeheader()
            for asset in bubble_assets:
                writer.writerow(asset)

    def backtest(self, backtest_start: int, backtest_end: int) -> None:
        for i in range(backtest_start, backtest_end, -1):
            test_date = du.days_ago(i)
            day_of_week = du.day_of_week(test_date)

            if day_of_week in ['Sunday', 'Monday']:
                print(f"Skipping {test_date} because it is a {day_of_week}.")
                continue

            print(f"Will run simulation for: {test_date}, Day of Week: {day_of_week}")
            self.discover_daily(test_date, should_optimize=True)


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description="Get number of days needed for backtesting.")

    # Add the --backtest argument
    parser.add_argument(
        "--backtest-start",
        type=int,
        nargs='?',
        help="Number of days to start the backtest from today (or the end date if specified).",
        const=DEFAULT_BACKTEST_DAYS_BACK_LPPLS,
        default=-1
    )
    parser.add_argument(
        "--backtest-end",
        type=int,
        nargs='?',
        help="Number of days to end the backtest from today. Requires --backtest-start to be set.",
        const=DEFAULT_BACKTEST_DAYS_BACK_LPPLS,
        default=-1
    )
    parser.add_argument("--specific", action="store_true", help="Plot only specific stocks")
    parser.add_argument("--profile", action="store_true", help="Enable profiling")

    # Parse the arguments
    args = parser.parse_args()

    # Check if --backtest-end is provided while --backtest-start is not
    if args.backtest_end != -1 and args.backtest_start == -1:
        parser.error("When specifying --backtest-end, you must also specify --backtest-start.")

    all_tickers = AllTickers()

    # Check if backtest argument is provided
    if args.profile:
        cProfile.run("AllTickers().backtest(123, 122)", "profile_output.pstats")
    elif args.specific:
        all_tickers.plot_specific(du.today())
    elif args.backtest_start != -1:
        all_tickers.backtest(args.backtest_start, args.backtest_end)
    else:
        all_tickers.discover_daily(du.today())



# To show only a specific set of tickers:
# python demo_all_tickers.py --specific

# To backtest:
# python demo_all_tickers.py --backtest-start 95

# To backtest with range:
# python demo_all_tickers.py --backtest-start 95 --backtest-end 90
