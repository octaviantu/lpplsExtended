import requests
from bs4 import BeautifulSoup
import psycopg2
import yfinance as yf
from datetime import datetime, timedelta
import argparse
from math import floor

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


def fetch_tickers(url: str) -> None:
    # Fetch the webpage content
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
    headers = [cell.text.strip() for cell in rows[0].find_all("th")]
    if "Avg Daily Share Volume" in headers[2] and "AUM" in headers[3]:
        VOLUME_ROW = 2
        AUM_ROW = 3
    elif "Avg Daily Share Volume" in headers[3] and "AUM" in headers[2]:
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


def fetch_and_store_pricing_history():
    # Connect to the database
    conn = psycopg2.connect(
        host="localhost", database="asset_prices", user="sornette", password="sornette", port="5432"
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fetch-tickers",
        action="store_true",
        help="Fetch all the tickers for the largest and most traaded ETFs",
    )
    args = parser.parse_args()

    if args.fetch_tickers:
        fetch_tickers(LARGEST_BY_SIZE)
        fetch_tickers(LARGEST_BY_VOLUME)

    fetch_and_store_pricing_history()


# To fetch largest and most traded ETF tickers:
# python parseLargestETFs.py --fetch-tickers
