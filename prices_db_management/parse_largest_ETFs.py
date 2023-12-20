import requests
from bs4 import BeautifulSoup
import psycopg2
import argparse
from math import floor
from fetch_common import is_banned, Asset
from parse_base import ParseBase

LARGEST_BY_SIZE = "https://etfdb.com/compare/market-cap/"
LARGEST_BY_VOLUME = "https://etfdb.com/compare/volume/"


class ParseLargetsETFs(ParseBase):
    def fetch_tickers(self, url: str) -> None:
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

        conn = self.get_connection()
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

            if is_banned(ticker, etf):
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

    def main(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--fetch-tickers",
            action="store_true",
            help="Fetch all the tickers for the largest and most traaded ETFs",
        )
        args = parser.parse_args()

        if args.fetch_tickers:
            self.fetch_tickers(LARGEST_BY_SIZE)
            self.fetch_tickers(LARGEST_BY_VOLUME)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT ticker, etf FROM etfs ORDER BY CAST(aum as FLOAT) DESC")
        rows = cursor.fetchall()
        assets = [Asset(ticker=row[0], name=row[1]) for row in rows]
        cursor.close()
        conn.close()

        self.fetch_and_store_pricing_history(asset_type="ETF", assets=assets)


if __name__ == "__main__":
    ParseLargetsETFs().main()


# To fetch largest and most traded ETF tickers:
# python parse_largest_ETFs.py --fetch-tickers
