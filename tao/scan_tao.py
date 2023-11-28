import sys
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/prices_db_management"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/common"
)

import psycopg2
from typing import List, Tuple, Dict
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.momentum import StochasticOscillator
from ta.trend import ADXIndicator
import pandas as pd
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from tao_dataclasses import PriceData, FullTechnicalData, TipTechnicalData, ATR_RANGE
from db_dataclasses import OrderType, Suggestion
from tao_suggestions import TaoSuggestions
import matplotlib.pyplot as plt
import os
from datetime import datetime
from price_technicals import PriceTechnicals
from typechecking import TypeCheckBase
from date_utils import DateUtils as du

MAX_NEEDED_DATA_POINTS = 2 * 89

# Define the connection parameters to the database
conn_params = {
    "host": DB_HOST,
    "database": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "port": DB_PORT,
}


class ScanTao(TypeCheckBase):
    # Define a function to calculate indicators and check conditions for each ticker
    def compute_technical_data(
        self, prices: List[PriceData]
    ) -> Tuple[FullTechnicalData, TipTechnicalData]:
        # Extract close prices into a list
        close_prices = [p.close_price for p in prices]

        # Convert list of prices to a pandas Series
        prices_series = pd.Series(close_prices)

        # Calculate EMAs
        ema_8 = EMAIndicator(prices_series, window=8).ema_indicator()
        ema_21 = EMAIndicator(prices_series, window=21).ema_indicator()
        ema_34 = EMAIndicator(prices_series, window=34).ema_indicator()
        ema_55 = EMAIndicator(prices_series, window=55).ema_indicator()
        ema_89 = EMAIndicator(prices_series, window=89).ema_indicator()

        # TODO(octaviant) - maybe change window to higher number - computing smoothed 3 over 8 is pretty morononic(overfitting++++)
        stoch = StochasticOscillator(
            high=prices_series, low=prices_series, close=prices_series, window=8, smooth_window=3
        )
        slow_stoch_d = stoch.stoch_signal()

        # Calculate ADX
        # TODO(octavian) - maybe increase this window because on the price chart I don't see it trending
        adx_i = ADXIndicator(high=prices_series, low=prices_series, close=prices_series, window=13)
        adx = adx_i.adx()

        rsi = RSIIndicator(prices_series, window=2).rsi()

        # Check the last data point for conditions
        fullTechnicalData = FullTechnicalData(
            ema_8=ema_8,
            ema_21=ema_21,
            ema_34=ema_34,
            ema_55=ema_55,
            ema_89=ema_89,
            slow_stoch_d=slow_stoch_d,
            adx=adx,
            rsi=rsi,
        )
        tipTechnicalData = TipTechnicalData(
            ema_8=ema_8.iloc[-1],
            ema_21=ema_21.iloc[-1],
            ema_34=ema_34.iloc[-1],
            ema_55=ema_55.iloc[-1],
            ema_89=ema_89.iloc[-1],
            slow_stoch_d=slow_stoch_d.iloc[-1],
            adx=adx.iloc[-1],
            rsi_yesterday=rsi.iloc[-2],
            rsi_today=rsi.iloc[-1],
        )

        return fullTechnicalData, tipTechnicalData

    def is_bull(self, td: TipTechnicalData) -> bool:
        ema_condition = (
            td.ema_8 >= td.ema_21
            and td.ema_21 >= td.ema_34
            and td.ema_34 >= td.ema_55
            and td.ema_55 >= td.ema_89
        )

        slow_stoch_condition = td.slow_stoch_d <= 40
        adx_condition = td.adx >= 20
        rsi_condition = td.rsi_yesterday <= 10 and td.rsi_today > 10

        return bool(ema_condition and slow_stoch_condition and adx_condition and rsi_condition)

    def is_bear(self, td: TipTechnicalData) -> bool:
        ema_condition = (
            td.ema_8 <= td.ema_21
            and td.ema_21 <= td.ema_34
            and td.ema_34 <= td.ema_55
            and td.ema_55 <= td.ema_89
        )

        slow_stoch_condition = td.slow_stoch_d >= 60
        adx_condition = td.adx >= 20
        rsi_condition = td.rsi_yesterday >= 90 and td.rsi_today < 90

        return bool(ema_condition and slow_stoch_condition and adx_condition and rsi_condition)

    def main(self):
        # Establish the connection to the database
        conn = psycopg2.connect(**conn_params)

        # Retrieve only the prices needed for the analysis
        query = f"""
            SELECT date, ticker, close_price, high_price, low_price
            FROM (
                SELECT date, ticker, close_price, high_price, low_price,
                    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn 
                FROM pricing_history
            ) sub
            WHERE rn <= {MAX_NEEDED_DATA_POINTS}
            ORDER BY date ASC, ticker
        """

        # Execute the query
        cursor = conn.cursor()
        cursor.execute(query)

        # Fetch all the data
        data = cursor.fetchall()

        # Close the cursor and the connection
        cursor.close()
        conn.close()

        # Convert the fetched data into a list of PriceData instances
        price_data_list = [
            PriceData(
                date_ordinal=du.date_to_ordinal(d[0]),
                ticker=d[1],
                close_price=d[2],
                high_price=d[3],
                low_price=d[4],
            )
            for d in data
        ]

        # Group the price data by ticker
        grouped_data: Dict[str, List[PriceData]] = {}
        for data in price_data_list:
            if data.ticker not in grouped_data:
                grouped_data[data.ticker] = []
            grouped_data[data.ticker].append(data)

        current_date = datetime.now().strftime("%Y-%m-%d")
        buy_plots_dir = f"plots/tao/{current_date}/buy"
        sell_plots_dir = f"plots/tao/{current_date}/sell"
        os.makedirs(buy_plots_dir, exist_ok=True)
        os.makedirs(sell_plots_dir, exist_ok=True)

        price_technicals = PriceTechnicals()

        # Check each ticker and collect those that satisfy the conditions
        suggestions = []
        for ticker, prices in grouped_data.items():
            fullTechnicalData, tipTechnicalData = self.compute_technical_data(prices)
            order_type = None
            if self.is_bull(tipTechnicalData):
                order_type = OrderType.BUY
            elif self.is_bear(tipTechnicalData):
                order_type = OrderType.SELL

            if order_type:
                suggestions.append(
                    Suggestion(
                        order_type=order_type,
                        ticker=ticker,
                        confidence=1.0,
                        price=prices[-1].close_price,
                        open_date=prices[-1].date_ordinal,
                    )
                )

                plot_dir = buy_plots_dir if order_type == "BUY" else sell_plots_dir

                # Plotting
                dates = [du.ordinal_to_date(p.date_ordinal) for p in prices]
                close_prices = [p.close_price for p in prices]
                plt.figure(figsize=(10, 6))
                plt.plot(dates, close_prices, label="Close Price")
                plt.title(f"{ticker} Close Prices")
                plt.xlabel("Date")
                plt.ylabel("Price")
                plt.legend()
                plot_path = os.path.join(plot_dir, f"{ticker}.png")
                plt.savefig(plot_path)
                plt.close()

                # Additional Plotting for Technical Indicators
                plt.figure(figsize=(15, 10))

                # Plotting Close Prices
                plt.subplot(511)
                plt.plot(dates, close_prices, label="Close Price")
                plt.title(f"{ticker} Technical Analysis")
                plt.legend()

                # Plotting EMAs
                plt.subplot(512)
                plt.plot(dates, close_prices, label="Close Price")
                plt.plot(dates, fullTechnicalData.ema_8, label="EMA 8")
                plt.plot(dates, fullTechnicalData.ema_21, label="EMA 21")
                plt.plot(dates, fullTechnicalData.ema_34, label="EMA 34")
                plt.plot(dates, fullTechnicalData.ema_55, label="EMA 55")
                plt.plot(dates, fullTechnicalData.ema_89, label="EMA 89")
                plt.legend()

                # Plotting Stochastic Oscillator
                plt.subplot(513)
                plt.plot(dates, fullTechnicalData.slow_stoch_d, label="Slow Stoch D", color="green")
                plt.axhline(y=40, color="grey", linestyle="--")
                plt.axhline(y=60, color="grey", linestyle="--")
                plt.legend()

                # Plotting ADX
                plt.subplot(514)
                plt.plot(dates, fullTechnicalData.adx, label="ADX", color="green")
                plt.axhline(y=20, color="grey", linestyle="--")
                plt.legend()

                # Plotting RSI
                plt.subplot(515)
                plt.plot(dates, fullTechnicalData.rsi, label="RSI", color="green")
                plt.axhline(y=10, color="grey", linestyle="--")
                plt.axhline(y=90, color="grey", linestyle="--")
                plt.legend()

                # Save the plot
                plot_path = os.path.join(plot_dir, f"{ticker}_technical.png")
                plt.tight_layout()
                plt.savefig(plot_path)
                plt.close()

                # Plot ATRs
                atrs = price_technicals.calculate_atr(prices)
                central_line = EMAIndicator(
                    pd.Series(close_prices), window=ATR_RANGE
                ).ema_indicator()[ATR_RANGE:]

                # Plotting logic
                plt.figure(figsize=(15, 10))

                # Plotting Close Prices
                plt.plot(dates, close_prices, label="Close Price", color="blue")
                plt.plot(
                    dates[ATR_RANGE:],
                    central_line,
                    label="Central EMA",
                    color="gray",
                    linestyle="--",
                )

                # Plot ATR lines at various multiples based on the central line
                atr_colors = ["green", "red", "cyan", "magenta", "yellow", "black"]
                for multiplier, color in zip([1, 2, 3], atr_colors):
                    matr = [multiplier * atr for atr in atrs]
                    upper_band = central_line + matr
                    lower_band = central_line - matr
                    plt.plot(
                        dates[ATR_RANGE:],
                        upper_band,
                        label=f"{multiplier} ATR Upper",
                        color=color,
                        linestyle="--",
                    )
                    plt.plot(
                        dates[ATR_RANGE:],
                        lower_band,
                        label=f"{multiplier} ATR Lower",
                        color=color,
                        linestyle="--",
                    )

                plt.title(f"{ticker} Close Prices with ATR Lines")
                plt.xlabel("Date")
                plt.ylabel("Price")
                plt.legend()

                # Save the plot
                plot_path = os.path.join(plot_dir, f"{ticker}_ATRs.png")
                plt.tight_layout()
                plt.savefig(plot_path)
                plt.close()

        TaoSuggestions().write_suggestions(suggestions)

        # Output the tickers that satisfy the conditions
        for suggestion in suggestions:
            print(f"{suggestion.order_type.value} {suggestion.ticker}")


if __name__ == "__main__":
    ScanTao().main()
