import sys

sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/prices_db_management"
)
sys.path.append("/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/tao")
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/common"
)

from tao_suggestions import TaoSuggestions
from lppls_suggestions import LpplsSuggestions
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from db_dataclasses import StrategyResult, ClosedPosition
import psycopg2
import os
from typechecking import TypeCheckBase
from date_utils import DateUtils as du
import argparse
from typing import List


DEFAULT_BACKTEST_DAYS_BACK = 95
PREVIOUS_PERF_DIR = "plots/previous_performance"
DAILY_DIR = PREVIOUS_PERF_DIR + "/daily"
HISTORIC_DIR = PREVIOUS_PERF_DIR + "/historic"


class ScorePreviousResults(TypeCheckBase):
    def score_end_day(self, test_date: str) -> None:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
        )

        # TaoSuggestions
        tao_suggestions = TaoSuggestions()
        tao_closed_now = tao_suggestions.score_previous_suggestions(conn, test_date)
        tao_all_closed = tao_suggestions.fetch_all_closed_suggestions(conn)

        # LpplsSuggestions
        lppls_suggestions = LpplsSuggestions()
        lppls_closed_now = lppls_suggestions.score_previous_suggestions(conn, test_date)
        lppls_all_closed = lppls_suggestions.fetch_all_closed_suggestions(conn)

        daily_dir_path = os.path.join(DAILY_DIR, test_date)
        self.write_historic_aggregate_results(
            [tao_closed_now, lppls_closed_now], daily_dir_path + "/daily-aggregate.csv"
        )
        self.write_historic_aggregate_results(
            [tao_all_closed, lppls_all_closed], daily_dir_path + "/historic-aggregate.csv"
        )

        self.write_closed_positions(
            tao_closed_now.closed_positions, daily_dir_path + "/tao-positions.csv"
        )
        self.write_closed_positions(
            lppls_closed_now.closed_positions, daily_dir_path + "/lppls-positions.csv"
        )

        self.write_closed_positions(
            tao_all_closed.closed_positions, HISTORIC_DIR + "/tao-all-positions.csv"
        )
        self.write_closed_positions(
            lppls_all_closed.closed_positions, HISTORIC_DIR + "/lppls-all-positions.csv"
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
                "Ticker, Open Date, Open Price, Close Date, Close Price, Position Size, Strategy Type, Close Reason, Order Type, Profit Percent, Profit Absolute\n"
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

                # Calling methods of ClosedPosition
                profit_percent = position.compute_profit_percent()
                profit_absolute = round(position.compute_profit_absolute(), 2)

                # Writing data to the file
                file.write(
                    f"{ticker}, {open_date}, {open_price}, {close_date}, {close_price}, {position_size}, {strategy_type}, {close_reason}, {order_type}, {profit_percent}, {profit_absolute}\n"
                )

    def write_historic_aggregate_results(
        self, strategyResults: List[StrategyResult], file_path: str
    ) -> None:
        all_closed_positions = [sr.closed_positions for sr in strategyResults]
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
                successful_count = result.succesful_count
                timeout_count = result.timeout_count
                stop_loss_count = result.stop_loss_count
                paid = round(result.paid, 2)
                received = round(result.received, 2)
                closed_positions = len(
                    result.closed_positions
                )  # Assuming you want the count of closed positions

                # Calling methods of StrategyResult
                profit_percent = result.compute_profit_percent()
                profit_absolute = round(result.compute_profit_absolute(), 2)
                trade_count = round(result.compute_trade_count(), 2)

                # Writing data to the file
                file.write(
                    f"{strategy_type}, {successful_count}, {timeout_count}, {stop_loss_count}, {paid}, {received}, {closed_positions}, {profit_percent}, {profit_absolute}, {trade_count}\n"
                )

    def backtest(self, days_ago: int = 95):
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

    # Parse the arguments
    args = parser.parse_args()

    # Check if backtest argument is provided
    if args.backtest != -1:
        ScorePreviousResults().backtest(days_ago=args.backtest)
    else:
        ScorePreviousResults().score_end_day(du.today())
