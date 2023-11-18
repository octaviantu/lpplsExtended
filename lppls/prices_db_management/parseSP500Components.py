import requests
from bs4 import BeautifulSoup
import psycopg2
import yfinance as yf
from datetime import datetime, timedelta
import argparse


slickcharts_to_yahoo_ticker_mapping = {"BRK.B": "BRK-B", "BF.B": "BF-B"}


def fetch_tickers():
    # Fetch the webpage content
    url = "https://www.slickcharts.com/sp500"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    response = requests.get(url, headers=headers)

    # Parse the HTML content
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the table and its rows
    table = soup.find("table", {"class": "table"})
    rows = table.find_all("tr")

    # Connect to the database
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sp500_components (
            id SERIAL PRIMARY KEY,
            company VARCHAR(255) NOT NULL,
            ticker VARCHAR(10) UNIQUE NOT NULL,
            portfolio_percent FLOAT NOT NULL
        )
    """
    )

    # Insert data into the sp500_components table
    for row in rows[1:]:
        cells = row.find_all("td")
        company = cells[1].text.strip()
        ticker = cells[2].text.strip()
        portfolio_percent = cells[3].text.strip().replace("%", "")
        cur.execute(
            "INSERT INTO sp500_components (company, ticker, portfolio_percent) VALUES (%s, %s, %s) ON CONFLICT (ticker) DO NOTHING",
            (company, ticker, portfolio_percent),
        )

    conn.commit()
    cur.close()
    conn.close()


def fetch_and_store_pricing_history():
    # Connect to the database
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()

    # Fetch the top 50 largest companies by portfolio percentage
    cursor.execute(
        "SELECT ticker, company FROM sp500_components ORDER BY CAST(portfolio_percent as FLOAT) DESC"
    )
    tickers = cursor.fetchall()

    # Fetch stock data and insert into the database
    for ticker, company in tickers:
        if ticker in slickcharts_to_yahoo_ticker_mapping:
            ticker = slickcharts_to_yahoo_ticker_mapping[ticker]

        # Check if ticker exists in the database
        cursor.execute("SELECT MAX(date) FROM pricing_history WHERE ticker = %s", (ticker,))
        last_date = cursor.fetchone()[0]

        if last_date is None:  # If ticker doesn't exist, fetch all the data in the last 4 years
            start_date = (datetime.now() - timedelta(days=4 * 365)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
        else:
            # If the last day is today or the previous working day, do nothing
            if (
                last_date == datetime.now().date()
                or last_date == (datetime.now() - timedelta(days=1)).date()
            ):
                continue
            else:  # Fetch the data from the last day until now
                start_date = last_date.strftime("%Y-%m-%d")
                end_date = datetime.now().strftime("%Y-%m-%d")

        # Fetch the stock data
        pricing_history = yf.download(ticker, start=start_date, end=end_date)
        for index, row in pricing_history.iterrows():
            cursor.execute(
                """
                INSERT INTO pricing_history (date, ticker, type, name, open_price, high_price, low_price, close_price, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, ticker, type)
                DO UPDATE SET open_price=EXCLUDED.open_price, high_price=EXCLUDED.high_price, low_price=EXCLUDED.low_price, close_price=EXCLUDED.close_price, volume=EXCLUDED.volume;
            """,
                (
                    index,
                    ticker,
                    "STOCK",
                    company,
                    row["Open"],
                    row["High"],
                    row["Low"],
                    row["Adj Close"],
                    row["Volume"],
                ),
            )

        conn.commit()

    cursor.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fetch-tickers", action="store_true", help="Fetch all the tickers for S&P500 components"
    )
    args = parser.parse_args()

    if args.fetch_tickers:
        fetch_tickers()

    fetch_and_store_pricing_history()


# To fetch S&P500 tickers:
# python parseSP500Components.py --fetch-tickers
