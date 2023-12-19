import requests
from bs4 import BeautifulSoup
import argparse
from parse_base import ParseBase
from fetch_common import is_banned, Asset, SLICKCHARTS_TO_YAHOO_TICKER_MAPPING


MOST_ACTIVE_FETCH_COUNT = 200


class ParseMostTradedStocksUS(ParseBase):
    def fetch_most_traded_tickers(self):
        url = f"https://finance.yahoo.com/most-active/?offset=0&count={MOST_ACTIVE_FETCH_COUNT}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", {"class": "W(100%)"})
        rows = table.find_all("tr")

        conn = self.get_connection()
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
            if ticker in SLICKCHARTS_TO_YAHOO_TICKER_MAPPING:
                ticker = SLICKCHARTS_TO_YAHOO_TICKER_MAPPING[ticker]

            company = cells[1].text.strip()

            if is_banned(ticker, company):
                continue

            cur.execute(
                "INSERT INTO stocks_us_most_traded (company, ticker) VALUES (%s, %s) ON CONFLICT (ticker) DO NOTHING",
                (company, ticker),
            )

        conn.commit()
        cur.close()
        conn.close()

    def main(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--fetch-tickers", action="store_true", help="Fetch most traded US stocks"
        )
        args = parser.parse_args()

        if args.fetch_tickers:
            self.fetch_most_traded_tickers()

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT ticker, company FROM stocks_us_most_traded")
        rows = cursor.fetchall()
        assets = [Asset(ticker=row[0], name=row[1]) for row in rows]
        cursor.close()
        conn.close()

        self.fetch_and_store_pricing_history(asset_type="STOCK", assets=assets)


if __name__ == "__main__":
    ParseMostTradedStocksUS().main()


# To fetch most traded tickers:
# python parse_most_traded_stocks_US.py --fetch-tickers
