from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from fetch_common import Asset
from typechecking import TypeCheckBase
from date_utils import DateUtils as du
import psycopg2
from typing import List
import yfinance as yf


class ParseBase(TypeCheckBase):
    def get_connection(self):
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
        )

    def fetch_and_store_pricing_history(self, asset_type: str, assets: List[Asset]) -> None:
        # Connect to the database
        conn = self.get_connection()
        cursor = conn.cursor()

        # Fetch stock data and insert into the database
        for asset in assets:
            # Check if ticker exists in the database
            cursor.execute(
                "SELECT MAX(date) FROM pricing_history WHERE ticker = %s", (asset.ticker,)
            )
            last_date = cursor.fetchone()[0]

            if last_date is None:  # If ticker doesn't exist, fetch all the data in the last 4 years
                start_date = du.days_ago(4 * 365)  # 4 years ago
                end_date = du.today()
            else:
                # If the last day is today, do nothing
                if last_date == du.today():
                    continue
                else:  # Fetch the data from the last day until now
                    start_date = last_date.strftime("%Y-%m-%d")
                    end_date = du.today()

            # Fetch the stock data
            pricing_history = yf.download(asset.ticker, start=start_date, end=end_date)

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
                        asset.ticker,
                        asset_type,
                        asset.name,
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
