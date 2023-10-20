import subprocess
import time

scripts_to_run = [
    {
        "cmd": ("python", "lppls/prices_db_management/parseLargestETFs.py"),
        "log": "Fetching latest ETF pricing",
    },
    {
        "cmd": ("python", "lppls/prices_db_management/parseMostTradedStocksUS.py"),
        "log": "Fetching most traded 100 stocks and their pricing",
    },
    {
        "cmd": ("python", "lppls/prices_db_management/parseSP500Components.py", "--fetch-tickers"),
        "log": "Fetching latest S&P500 pricing",
    },
    {
        "cmd": ("python", "lppls/demo/demoSP.py"),
        "log": "Running fits on all available stocks and etfs",
    },
]

total_start_time = time.time()
for script in scripts_to_run:
    print(script["log"])
    script_start_time = time.time()

    subprocess.run(script["cmd"])

    script_end_time = time.time()
    script_elapsed_time = script_end_time - script_start_time
    print(f"{script['log']} took {script_elapsed_time:.2f} seconds.\n")

total_end_time = time.time()
total_elapsed_time = total_end_time - total_start_time
print(f"Total execution took {total_elapsed_time:.2f} seconds.\n")
