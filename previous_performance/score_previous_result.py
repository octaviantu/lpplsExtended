from prices_db_management.tao_suggestions import TaoSuggestions
from prices_db_management.lppls_suggestions import LpplsSuggestions
from prices_db_management.db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from prices_db_management.db_dataclasses import StrategyResult, ClosedPosition
import psycopg2
import os
from common.typechecking import TypeCheckBase
from common.date_utils import DateUtils as du
import argparse
from typing import List
import shutil
from copy import deepcopy


DEFAULT_BACKTEST_DAYS_BACK = 95
PREVIOUS_PERF_DIR = "plots/previous_performance"
DAILY_DIR = PREVIOUS_PERF_DIR + "/daily"
HISTORIC_DIR = PREVIOUS_PERF_DIR + "/historic"


class ScorePreviousResults(TypeCheckBase):
    def score_end_day(self, test_date: str) -> None:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
        )

        daily_dir_path = os.path.join(DAILY_DIR, test_date)

        # TaoSuggestions
        tao_suggestions = TaoSuggestions()
        tao_closed_now = tao_suggestions.score_previous_suggestions(conn, test_date)
        tao_all_closed = tao_suggestions.fetch_all_closed_suggestions(conn)

        self.write_closed_positions(
            tao_closed_now.get_closed_positions(), daily_dir_path + "/tao-positions.csv"
        )
        self.write_closed_positions(
            tao_all_closed.get_closed_positions(), HISTORIC_DIR + "/tao-all-positions.csv"
        )

        # LpplsSuggestions
        lppls_suggestions = LpplsSuggestions()
        lppls_closed_now = lppls_suggestions.score_previous_suggestions(conn, test_date)
        lppls_all_closed = lppls_suggestions.fetch_all_closed_suggestions(conn)

        self.write_closed_positions(
            lppls_closed_now.get_closed_positions(), daily_dir_path + "/lppls-positions-1day.csv"
        )
        self.write_closed_positions(
            lppls_all_closed.get_closed_positions(), HISTORIC_DIR + "/lppls-all-positions-1day.csv"
        )

        # TODO(octaviant) - fix this weird way of having separate objects
        lppls_closed_now_3_days = deepcopy(lppls_closed_now)
        lppls_closed_now_3_days.desired_recommendation_count = 3
        lppls_all_closed_3_days = deepcopy(lppls_all_closed)
        lppls_all_closed_3_days.desired_recommendation_count = 3

        self.write_closed_positions(
            lppls_closed_now_3_days.get_closed_positions(),
            daily_dir_path + "/lppls-positions-3days.csv",
        )
        self.write_closed_positions(
            lppls_all_closed_3_days.get_closed_positions(),
            HISTORIC_DIR + "/lppls-all-positions-3days.csv",
        )

        self.write_aggregate_results(
            [tao_closed_now, lppls_closed_now, lppls_closed_now_3_days],
            daily_dir_path + "/daily-aggregate.csv",
        )

        self.write_aggregate_results(
            [tao_all_closed, lppls_all_closed, lppls_all_closed_3_days],
            daily_dir_path + "/historic-aggregate.csv",
        )

        conn.close()

    def write_closed_positions(
        self, closed_positions: List[ClosedPosition], file_path: str
    ) -> None:
        if len(closed_positions) == 0:
            return

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as file:
            # Write the header line
            file.write(
                "Ticker, Open Date, Open Price, Close Date, Close Price, Position Size, Strategy Type, Close Reason, Order Type, Daily runs count, Profit Percent, Profit Absolute\n"
            )

            for position in closed_positions:
                # Extracting each field
                ticker = position.ticker
                open_date = position.open_date
                open_price = round(position.open_price, 2)
                close_date = position.close_date
                close_price = round(position.close_price, 2)
                position_size = round(position.position_size, 2)
                strategy_type = position.strategy_type.value
                close_reason = position.close_reason.value
                order_type = position.order_type.value
                daily_runs_count = position.daily_runs_count

                # Calling methods of ClosedPosition
                profit_percent = position.compute_profit_percent()
                profit_absolute = round(position.compute_profit_absolute(), 2)

                # Writing data to the file
                file.write(
                    f"{ticker}, {open_date}, {open_price}, {close_date}, {close_price}, {position_size}, {strategy_type}, {close_reason}, {order_type}, {daily_runs_count}, {profit_percent}, {profit_absolute}\n"
                )

    def write_aggregate_results(
        self, strategyResults: List[StrategyResult], file_path: str
    ) -> None:
        all_closed_positions = [sr.get_closed_positions() for sr in strategyResults]
        if len(all_closed_positions) == 0:
            return

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as file:
            # Write the header line
            file.write(
                "Strategy Type, Successful Count, Timeout Count, Stop Loss Count, Paid, Received, Closed Positions, Profit Percent, Profit Absolute, Trade Count\n"
            )

            for result in strategyResults:
                # Extracting each field
                strategy_type = result.strategy_type.value

                agg = result.aggregate_counts()
                successful_count = agg.succesful_count
                timeout_count = agg.timeout_count
                stop_loss_count = agg.stop_loss_count
                paid = round(agg.paid, 2)
                received = round(agg.received, 2)
                closed_positions = len(
                    result.get_closed_positions()
                )  # Assuming you want the count of closed positions

                # Calling methods of StrategyResult
                profit_percent = result.compute_profit_percent()
                profit_absolute = round(result.compute_profit_absolute(), 2)
                trade_count = round(result.compute_trade_count(), 2)

                # Writing data to the file
                file.write(
                    f"{strategy_type}, {successful_count}, {timeout_count}, {stop_loss_count}, {paid}, {received}, {closed_positions}, {profit_percent}, {profit_absolute}, {trade_count}\n"
                )

    def backtest(self, days_ago: int = 95, should_clear_previous: bool = False) -> None:
        if should_clear_previous:
            if os.path.exists(PREVIOUS_PERF_DIR):
                # Remove the directory and all its contents
                shutil.rmtree(PREVIOUS_PERF_DIR)
            else:
                print(f"Directory {PREVIOUS_PERF_DIR} does not exist.")

            conn = psycopg2.connect(
                host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
            )
            cursor = conn.cursor()
            update_query = """
            UPDATE suggestions
            SET is_position_open = TRUE,
                close_date = NULL,
                close_price = NULL,
                close_reason = NULL
            WHERE NOT is_position_open;
            """

            # Execute the query
            cursor.execute(update_query)

            # Commit the changes to the database
            conn.commit()
            conn.close()

        for i in range(days_ago, -1, -1):
            self.score_end_day(du.days_ago(i))


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description="Get number of days needed for backtesting.")

    # Add the --backtest argument
    parser.add_argument(
        "--backtest",
        type=int,
        nargs="?",
        help="Number of days to run the backtest for",
        const=95,
        default=-1,
    )
    # Add the --clear-previous argument
    parser.add_argument("--clear-previous", action="store_true", help="Clear previous results")

    # Parse the arguments
    args = parser.parse_args()

    # Check if backtest argument is provided
    if args.backtest != -1:
        ScorePreviousResults().backtest(
            days_ago=args.backtest, should_clear_previous=args.clear_previous
        )
    elif args.clear_previous:
        parser.error("--clear-previous requires --backtest")
    else:
        ScorePreviousResults().score_end_day(du.today())
