import sys

sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/prices_db_management"
)

import psycopg2
from typing import List
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.momentum import StochasticOscillator
from ta.trend import ADXIndicator
import pandas as pd
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from tao_dataclasses import PriceData, TechnicalData
from db_dataclasses import Suggestion
from tao_suggestions import TaoSuggestions

MAX_NEEDED_DATA_POINTS = 2 * 89

# Define the connection parameters to the database
conn_params = {
    "host": DB_HOST,
    "database": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "port": DB_PORT
}

# Establish the connection to the database
conn = psycopg2.connect(**conn_params)

# Retrieve only the prices needed for the analysis
query = f"""
    SELECT date, ticker, close_price 
    FROM (
        SELECT date, ticker, close_price, 
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
price_data_list = [PriceData(date=pd.Timestamp.toordinal(d[0]), ticker=d[1], close_price=d[2]) for d in data]

# Group the price data by ticker
grouped_data = {}
for data in price_data_list:
    if data.ticker not in grouped_data:
        grouped_data[data.ticker] = []
    grouped_data[data.ticker].append(data)

# Define a function to calculate indicators and check conditions for each ticker
def compute_technical_data(prices: List[PriceData]):
    # Extract close prices into a list
    close_prices = [p.close_price for p in prices]
    
    # Convert list of prices to a pandas Series
    prices_series = pd.Series(close_prices)
    
    # Calculate EMAs
    ema_8 = EMAIndicator(prices_series, window=8).ema_indicator().iloc[-1]
    ema_21 = EMAIndicator(prices_series, window=21).ema_indicator().iloc[-1]
    ema_34 = EMAIndicator(prices_series, window=34).ema_indicator().iloc[-1]
    ema_55 = EMAIndicator(prices_series, window=55).ema_indicator().iloc[-1]
    ema_89 = EMAIndicator(prices_series, window=89).ema_indicator().iloc[-1]

    
    # TODO(octaviant) - maybe change window to higher number - computing smoothed 3 over 8 is pretty morononic(overfitting++++)
    stoch = StochasticOscillator(high=prices_series, low=prices_series, close=prices_series, window=8, smooth_window=3)
    slow_stoch_d = stoch.stoch_signal().iloc[-1]
    
    # Calculate ADX
    # TODO(octavian) - maybe increase this window because on the price chart I don't see it trending
    adx_i = ADXIndicator(high=prices_series, low=prices_series, close=prices_series, window=13)
    adx = adx_i.adx().iloc[-1]

    [rsi_yesterday, rsi_today] = RSIIndicator(prices_series, window=2).rsi().iloc[-2:]
    
    # Check the last data point for conditions
    return TechnicalData(ema_8=ema_8, ema_21=ema_21, ema_34=ema_34, ema_55=ema_55, ema_89=ema_89,
                        slow_stoch_d=slow_stoch_d, adx=adx, rsi_yesterday=rsi_yesterday, rsi_today=rsi_today)


def is_bull(td: TechnicalData) -> bool:
    ema_condition = (td.ema_8 >= td.ema_21 and td.ema_21 >= td.ema_34 and
                    td.ema_34 >= td.ema_55 and td.ema_55 >= td.ema_89)
    
    slow_stoch_condition = td.slow_stoch_d <= 40
    adx_condition = td.adx >= 20
    rsi_condition = td.rsi_yesterday <= 10 and td.rsi_today > 10

    return ema_condition and slow_stoch_condition and adx_condition and rsi_condition


def is_bear(td: TechnicalData) -> bool:
    ema_condition = (td.ema_8 <= td.ema_21 and td.ema_21 <= td.ema_34 and
                    td.ema_34 <= td.ema_55 and td.ema_55 <= td.ema_89)
    
    slow_stoch_condition = td.slow_stoch_d >= 60
    adx_condition = td.adx >= 20
    rsi_condition = td.rsi_yesterday >= 90 and td.rsi_today < 90

    return ema_condition and slow_stoch_condition and adx_condition and rsi_condition




# Check each ticker and collect those that satisfy the conditions
suggestions = []
for ticker, prices in grouped_data.items():
    technical_data = compute_technical_data(prices)
    order_type = None
    if is_bull(technical_data):
        order_type="BUY"
    elif is_bear(technical_data):
        order_type="SELL"

    if order_type:
        suggestions.append(Suggestion(order_type=order_type, ticker=ticker, confidence=1.0,
                                      price=prices[-1].close_price, open_date= prices[-1].date))
        
TaoSuggestions().write_suggestions(suggestions)


# Output the tickers that satisfy the conditions
for suggestion in suggestions:
    print(f'{suggestion.order_type} {suggestion.ticker}')
