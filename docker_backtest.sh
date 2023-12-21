#!/bin/bash

echo "Create DB if it doesn't exist"
python /usr/src/app/prices_db_management/create_db.py

echo "Fetching latest ETF pricing"
python /usr/src/app/prices_db_management/parse_largest_ETFs.py --fetch-tickers

echo "Fetching most traded 100 stocks and their pricing"
python /usr/src/app/prices_db_management/parse_most_traded_stocks_US.py --fetch-tickers

echo "Fetching latest S&P500 pricing"
python /usr/src/app/prices_db_management/parse_SP500_components.py --fetch-tickers

echo "Fetching latest Index pricing"
python /usr/src/app/prices_db_management/parse_indexes.py

echo "Running LPPLS fits on all available stocks and ETFs"
python /usr/src/app/lppls/demo/demo_all_tickers.py --backtest-start 200

# Add any additional commands you need to run
