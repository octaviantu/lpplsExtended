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

    # Find drawups and drawdowns
    peaks = Peaks()
    drawups = peaks.find_extremities(data, is_max=True)
    drawdowns = peaks.find_extremities(data, is_max=False)

    # Create subplots for drawups and drawdowns
    _, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(14, 10))

    # Plot the drawups
    ax1.plot(data['Date'], data['Adj Close'], label="Price", color="black", linewidth=0.75)
    for date, value in drawups.items():
        index = data.index[data['Date'] == date].tolist()
        if index:
            index = index[0]
            ax1.axvline(x=pd.to_datetime(date), color='red', linewidth=0.5)
            ax1.text(pd.to_datetime(date), data['Adj Close'][index], f'{date}({value:.2f})', color='red', rotation=90, verticalalignment='bottom')

    ax1.set_title('Drawups')

    # Plot the drawdowns
    ax2.plot(data['Date'], data['Adj Close'], label="Price", color="black", linewidth=0.75)
    for date, value in drawdowns.items():
        index = data.index[data['Date'] == date].tolist()
        if index:
            index = index[0]
            ax2.axvline(x=pd.to_datetime(date), color='blue', linewidth=0.5)
            ax2.text(pd.to_datetime(date), data['Adj Close'][index], f'{date}({value:.2f})', color='blue', rotation=90, verticalalignment='top')

    ax2.set_title('Drawdowns')
    plt.show()


if __name__ == "__main__":
    main()
