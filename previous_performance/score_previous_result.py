import sys

sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/prices_db_management"
)

sys.path.append("/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/tao")

from datetime import datetime
from tao_suggestions import TaoSuggestions
from lppls_suggestions import LpplsSuggestions
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
import psycopg2
import csv
import os


def main() -> None:
    conn = psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
    )

    # TaoSuggestions
    taoSuggestions = TaoSuggestions()
    tao_strategy_results = taoSuggestions.score_previous_suggestions(conn)

    # LpplsSuggestions
    lpplsSuggestions = LpplsSuggestions()
    lppls_strategy_results = lpplsSuggestions.score_previous_suggestions(conn)

    conn.close()

    # Prepare and write data for TaoSuggestions
    write_strategy_results(tao_strategy_results, first_call=True)

    # Prepare and write data for LpplsSuggestions
    write_strategy_results(lppls_strategy_results, first_call=False)


def write_strategy_results(strategy_results, first_call=True):
    # Prepare the data to be written
    data_to_write = {
        "strategy_type": strategy_results.strategy_type.value,
        "trade_count": strategy_results.compute_trade_count(),
        "succesful_count": strategy_results.succesful_count,
        "timeout_count": strategy_results.timeout_count,
        "profit": strategy_results.compute_profit(),
    }

    # Define the file path
    current_date = datetime.now().strftime("%Y-%m-%d")
    file_path = f"plots/previous_performance/{current_date}.csv"

    # Make sure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Determine file mode - overwrite if first call, append otherwise
    file_mode = "w" if first_call else "a"

    # Write or append the data to the CSV file
    with open(file_path, mode=file_mode, newline="") as file:
        writer = csv.DictWriter(file, fieldnames=data_to_write.keys())
        writer.writeheader()
        writer.writerow(data_to_write)


if __name__ == "__main__":
    main()
