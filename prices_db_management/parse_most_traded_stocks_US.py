import sys

sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/common"
)

import requests
from bs4 import BeautifulSoup
import psycopg2
import yfinance as yf
import argparse
from typechecking import TypeCheckBase
from date_utils import DateUtils as du

slickcharts_to_yahoo_ticker_mapping = {"BRK.B": "BRK-B"}

MOST_ACTIVE_FETCH_COUNT = 200

BANNED_TICKERS = [
    # The price is too low (close to 1), making my log formulas not work
    "GSAT"
]


class ParseMostTradedStocksUS(TypeCheckBase):
    @staticmethod
    def fetch_most_traded_tickers():
        url = f"https://finance.yahoo.com/most-active/?offset=0&count={MOST_ACTIVE_FETCH_COUNT}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", {"class": "W(100%)"})
        rows = table.find_all("tr")

        conn = psycopg2.connect(
            host="localhost",
            database="asset_prices",
            user="sornette",
            password="sornette",
            port="5432",
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

            if ticker in BANNED_TICKERS:
                continue

            cur.execute(
                "INSERT INTO stocks_us_most_traded (company, ticker) VALUES (%s, %s) ON CONFLICT (ticker) DO NOTHING",
                (company, ticker),
            )

        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def fetch_and_store_pricing_history():
        conn = psycopg2.connect(
            host="localhost",
            database="asset_prices",
            user="sornette",
            password="sornette",
            port="5432",
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
                start_date = du.days_ago(4 * 365)  # 4 years ago
                end_date = du.today()
            else:
                # If the last day is today or the previous working day, do nothing
                if last_date == du.today():
                    continue
                else:  # Fetch the data from the last day until now
                    start_date = last_date
                    end_date = du.today()

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

    @staticmethod
    def main():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--fetch-tickers", action="store_true", help="Fetch most traded US stocks"
        )
        args = parser.parse_args()

        if args.fetch_tickers:
            ParseMostTradedStocksUS.fetch_most_traded_tickers()

        ParseMostTradedStocksUS.fetch_and_store_pricing_history()


if __name__ == "__main__":
    ParseMostTradedStocksUS.main()


# To fetch most traded tickers:
# python parse_most_traded_stocks_US.py --fetch-tickers
