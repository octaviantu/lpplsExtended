import sys

sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/common"
)

import requests
from bs4 import BeautifulSoup
import psycopg2
import yfinance as yf
import argparse
from math import floor
from typechecking import TypeCheckBase
from date_utils import DateUtils as du

LARGEST_BY_SIZE = "https://etfdb.com/compare/market-cap/"
LARGEST_BY_VOLUME = "https://etfdb.com/compare/volume/"

# I don't want to trade leveraged ETFs - they decline in value because of their structure
BANNED_KEYWORDS = ["Bear ", "Bull ", "Leveraged ", "3X ", "2X ", "1.5X "]

BANNED_TICKERS = [
    # MMF - fluctuations irrelevant
    "SGOV",
    "USFR",
    "BIL",
    "SHV",
    # Short term treasury - fluctuations noisy
    "SHY",
    "VGSH",
]


class ParseLargetsETFs(TypeCheckBase):
    @staticmethod
    def fetch_tickers(url: str) -> None:
        # Fetch the webpage content
        request_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }
        response = requests.get(url, headers=request_headers)

        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the table and its rows
        table = soup.find("table", {"class": "table"})
        rows = table.find_all("tr")

        # Connect to the database
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
            CREATE TABLE IF NOT EXISTS etfs (
                id SERIAL PRIMARY KEY,
                etf VARCHAR(255) NOT NULL,
                ticker VARCHAR(10) UNIQUE NOT NULL,
                aum BIGINT NOT NULL,
                volume BIGINT NOT NULL
            )
        """
        )

        #  the webpages display the ETFs in different order
        table_headers = [cell.text.strip() for cell in rows[0].find_all("th")]
        if "Avg Daily Share Volume" in table_headers[2] and "AUM" in table_headers[3]:
            VOLUME_ROW = 2
            AUM_ROW = 3
        elif "Avg Daily Share Volume" in table_headers[3] and "AUM" in table_headers[2]:
            VOLUME_ROW = 3
            AUM_ROW = 2
        else:
            raise Exception("Aum and volume columns not as expected")

        # Insert data into the etfs table
        for row in rows[1:]:
            cells = row.find_all("td")
            ticker = cells[0].text.strip()
            etf = cells[1].text.strip()

            if any(keyword in etf for keyword in BANNED_KEYWORDS) or ticker in BANNED_TICKERS:
                continue

            aum = floor(float(cells[AUM_ROW].text.strip().replace("$", "").replace(",", "")))
            volume = int(cells[VOLUME_ROW].text.strip().replace(",", ""))
            cur.execute(
                "INSERT INTO etfs (etf, ticker, aum, volume) VALUES (%s, %s, %s, %s) ON CONFLICT (ticker) DO NOTHING",
                (etf, ticker, aum, volume),
            )

        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def fetch_and_store_pricing_history():
        # Connect to the database
        conn = psycopg2.connect(
            host="localhost",
            database="asset_prices",
            user="sornette",
            password="sornette",
            port="5432",
        )
        cursor = conn.cursor()

        # Fetch the top 50 largest companies by portfolio percentage
        cursor.execute("SELECT ticker, etf FROM etfs ORDER BY CAST(aum as FLOAT) DESC")
        tickers = cursor.fetchall()

        # Fetch stock data and insert into the database
        for ticker, etf in tickers:
            # Check if ticker exists in the database
            cursor.execute("SELECT MAX(date) FROM pricing_history WHERE ticker = %s", (ticker,))
            last_date = cursor.fetchone()[0]

            if last_date is None:  # If ticker doesn't exist, fetch all the data in the last 4 years
                start_date = du.days_ago(4 * 365) # 4 years ago
                end_date = du.today()
            else:
                # If the last day is today, do nothing
                if last_date == du.today():
                    continue
                else:  # Fetch the data from the last day until now
                    start_date = last_date.strftime("%Y-%m-%d")
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
                        "ETF",
                        etf,
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
            "--fetch-tickers",
            action="store_true",
            help="Fetch all the tickers for the largest and most traaded ETFs",
        )
        args = parser.parse_args()

        if args.fetch_tickers:
            ParseLargetsETFs.fetch_tickers(LARGEST_BY_SIZE)
            ParseLargetsETFs.fetch_tickers(LARGEST_BY_VOLUME)

        ParseLargetsETFs.fetch_and_store_pricing_history()


if __name__ == "__main__":
    ParseLargetsETFs.main()


# To fetch largest and most traded ETF tickers:
# python parse_largest_ETFs.py --fetch-tickers
