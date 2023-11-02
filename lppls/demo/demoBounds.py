import sys

sys.path.append("/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls")
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/metrics"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/bubble_bounds"
)

import pandas as pd
import psycopg2
import matplotlib.pyplot as plt
from peaks import Peaks


def main():
    # Fetch VLO data from the database
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()
    query = "SELECT date, close_price FROM pricing_history WHERE ticker='AAPL' ORDER BY date ASC;"
    cursor.execute(query)
    rows = cursor.fetchall()
    data = pd.DataFrame(rows, columns=["Date", "Adj Close"])

    drawups = Peaks().find_drawups(data)


    _, (ax1) = plt.subplots(nrows=1, ncols=1, sharex=True, figsize=(14, 8))
    ax1.plot(data['Date'], data['Adj Close'], label="price", color="black", linewidth=0.75)

    # Plot the vertical red bars and annotate
    for date, value in drawups.items():
        # Find the index for the date in the DataFrame
        index = data.index[data['Date'] == date].tolist()
        if index:  # Check if the date is found in the DataFrame
            index = index[0]
            ax1.axvline(x=pd.to_datetime(date), color='red', linewidth=0.5)
            ax1.text(pd.to_datetime(date), data['Adj Close'][index], f'{date}({value:.2f})', color='red', rotation=90, verticalalignment='bottom')

    plt.show()


if __name__ == "__main__":
    main()
