import requests
from bs4 import BeautifulSoup
import psycopg2
import yfinance as yf
from datetime import datetime, timedelta
import argparse


slickcharts_to_yahoo_ticker_mapping = {"BRK.B": "BRK-B"}

MOST_ACTIVE_FETCH_COUNT = 200

def fetch_most_traded_tickers():
    url = f"https://finance.yahoo.com/most-active/?offset=0&count={MOST_ACTIVE_FETCH_COUNT}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "W(100%)"})
    rows = table.find_all("tr")

    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stocks_us_most_traded (
            id SERIAL PRIMARY KEY,
            company VARCHAR(255) NOT NULL,
            ticker VARCHAR(10) UNIQUE NOT NULL
        )
    """
    )

    for row in rows[1:]:
        cells = row.find_all("td")
        ticker = cells[0].text.strip()
        company = cells[1].text.strip()

        cur.execute(
            "INSERT INTO stocks_us_most_traded (company, ticker) VALUES (%s, %s) ON CONFLICT (ticker) DO NOTHING",
            (company, ticker),
        )

    conn.commit()
    cur.close()
    conn.close()


def fetch_and_store_pricing_history():
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
    )
    cursor = conn.cursor()

    cursor.execute("SELECT ticker, company FROM stocks_us_most_traded")
    tickers = cursor.fetchall()

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
            if last_date == datetime.now().date():
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
    parser.add_argument("--fetch-tickers", action="store_true", help="Fetch most traded US stocks")
    args = parser.parse_args()

    if args.fetch_tickers:
        fetch_most_traded_tickers()

    fetch_and_store_pricing_history()


# To fetch most traded tickers:
# python parseMostTradedStocksUS.py --fetch-tickers
