import sys

sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/prices_db_management"
)

sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/tao"
)

from datetime import datetime
from tao_suggestions import TaoSuggestions
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
import psycopg2
import csv
import os



def main() -> None:
    conn = psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
    )

    taoSuggestions = TaoSuggestions()
    strategy_results = taoSuggestions.score_previous_suggestions(conn)
    conn.close()
    
    # Prepare the data to be written
    data_to_write = {
        'strategy_type': strategy_results.strategy_type,
        'trade_count': strategy_results.trade_count,
        'profit': strategy_results.getProfit()
    }
    
    # Define the file path
    current_date = datetime.now().strftime("%Y-%m-%d")
    file_path = f'plots/previous_performance/{current_date}.csv'
    
    # Make sure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Check if file exists, if not, write header as well
    file_exists = os.path.isfile(file_path)
    
    # Write or append the data to the CSV file
    with open(file_path, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data_to_write.keys())
        if not file_exists:
            writer.writeheader()  # Write header if the file is new
        writer.writerow(data_to_write)


if __name__ == "__main__":
    main()