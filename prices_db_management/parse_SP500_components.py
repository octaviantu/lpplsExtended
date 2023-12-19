import requests
from bs4 import BeautifulSoup
import argparse
from fetch_common import Asset, SLICKCHARTS_TO_YAHOO_TICKER_MAPPING
from parse_base import ParseBase


class ParseSP500Components(ParseBase):
    def fetch_tickers(self):
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
        conn = self.get_connection()
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
            if ticker in SLICKCHARTS_TO_YAHOO_TICKER_MAPPING:
                ticker = SLICKCHARTS_TO_YAHOO_TICKER_MAPPING[ticker]

            portfolio_percent = cells[3].text.strip().replace("%", "")
            cur.execute(
                "INSERT INTO sp500_components (company, ticker, portfolio_percent) VALUES (%s, %s, %s) ON CONFLICT (ticker) DO NOTHING",
                (company, ticker, portfolio_percent),
            )

        conn.commit()
        cur.close()
        conn.close()

    def main(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--fetch-tickers",
            action="store_true",
            help="Fetch all the tickers for S&P500 components",
        )
        args = parser.parse_args()

        if args.fetch_tickers:
            self.fetch_tickers()

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT ticker, company FROM sp500_components ORDER BY CAST(portfolio_percent as FLOAT) DESC"
        )
        rows = cursor.fetchall()
        assets = [Asset(ticker=row[0], name=row[1]) for row in rows]
        cursor.close()
        conn.close()

        self.fetch_and_store_pricing_history(asset_type="STOCK", assets=assets)


if __name__ == "__main__":
    ParseSP500Components().main()

# To fetch S&P500 tickers:
# python parse_SP500_components.py --fetch-tickers
