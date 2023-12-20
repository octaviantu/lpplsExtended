import subprocess
import time
from common.date_utils import DateUtils as du

scripts_to_run = [
    {
        "cmd": ("python", "prices_db_management/create_db.py"),
        "log": "Create DB if it doesn't exist",
    },
    {
        "cmd": ("python", "prices_db_management/parse_largest_ETFs.py", "--fetch-tickers"),
        "log": "Fetching latest ETF pricing",
    },
    {
        "cmd": ("python", "prices_db_management/parse_most_traded_stocks_US.py", "--fetch-tickers"),
        "log": "Fetching most traded 100 stocks and their pricing",
    },
    {
        "cmd": ("python", "prices_db_management/parse_SP500_components.py", "--fetch-tickers"),
        "log": "Fetching latest S&P500 pricing",
    },
    {
        "cmd": ("python", "prices_db_management/parse_indexes.py"),
        "log": "Fetching latest S&P500 pricing",
    },
    {
        "cmd": ("python", "lppls/demo/demo_all_tickers.py"),
        "log": "Running LPPLS fits on all available stocks and etfs",
    },
    {
        "cmd": ("python", "tao/scan_tao.py"),
        "log": "Running TAO on all available stocks and etfs",
    },
    {
        "cmd": ("python", "prices_db_management/backup_db.py"),
        "log": "Backup existing db state",
    },
    {
        "cmd": ("python", "previous_performance/score_previous_result.py"),
        "log": "Score previus suggestions",
    },
]


def main():
    #  Don't run simulation if today is a Sunday or Monday.
    test_date = du.today()
    day_of_week = du.day_of_week(test_date)

    if day_of_week in ["Sunday", "Monday"]:
        print(f"Skipping {test_date} because it is a {day_of_week}.")
        return

    print(f"Will run simulation for: {test_date}, Day of Week: {day_of_week}")

    # Run all scripts.
    total_start_time = time.time()
    for script in scripts_to_run:
        print(script["log"])
        script_start_time = time.time()

        subprocess.run(script["cmd"], check=True)

        script_end_time = time.time()
        script_elapsed_time = script_end_time - script_start_time
        print(f"{script['log']} took {script_elapsed_time:.2f} seconds.\n")

    total_end_time = time.time()
    total_elapsed_time = total_end_time - total_start_time
    print(f"Total execution took {total_elapsed_time:.2f} seconds.\n")


if __name__ == "__main__":
    main()
