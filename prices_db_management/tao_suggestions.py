from typing import List
from db_dataclasses import Suggestion, StrategyResults, StrategyType, OrderType, CloseReason
from tao_dataclasses import ATR_RANGE
from db_defaults import DEFAULT_POSITION_SIZE
from datetime import datetime, timedelta
from trade_suggestions import TradeSuggestions
from price_technicals import PriceTechnicals
from tao_dataclasses import PriceData, MAX_DAYS_UNTIL_CLOSE_POSITION_TAO
from psycopg2.extras import DictCursor


STRATEGY_TYPE = StrategyType.TAO_RSI

class TaoSuggestions(TradeSuggestions):
    def __init__(self):
        # Initialize the parent class
        super().__init__()
        self.price_technicals = PriceTechnicals()


    def maybe_insert_suggestions(self, suggestions: List[Suggestion], cursor) -> None:
        for suggestion in suggestions:
            if self.is_position_open(cursor, suggestion.ticker, STRATEGY_TYPE):
                continue

            formatted_open_date = datetime.fromordinal(suggestion.open_date).strftime("%Y-%m-%d")
            cursor.execute(
                """
                INSERT INTO suggestions (strategy_t, order_t, open_date, open_price, ticker, confidence, position_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (open_date, ticker, strategy_t) DO NOTHING
            """, (
                STRATEGY_TYPE.value,
                suggestion.order_type.value,

                formatted_open_date,
                suggestion.price,

                suggestion.ticker,
                suggestion.confidence,
                DEFAULT_POSITION_SIZE
            ))


    def is_eligible_to_close(self, order_type: OrderType, ticker: str, open_date: int, last_date: int, cursor) -> bool:

        # Get pricing data for the ticker
        cursor.execute("""
            SELECT date, ticker, close_price, high_price, low_price FROM pricing_history
            WHERE ticker = %s ORDER BY date DESC LIMIT %s;
        """, (ticker, ATR_RANGE + 1))
        rows = cursor.fetchall()

        pricing_data = [PriceData(
            date=row['date'], 
            ticker=row['ticker'], 
            close_price=row['close_price'],
            high_price=row['high_price'],
            low_price=row['low_price']
        ) for row in rows]    

        is_successful = self.price_technicals.is_outside_atr_band(pricing_data, order_type)
        is_timeout = open_date + timedelta(days=MAX_DAYS_UNTIL_CLOSE_POSITION_TAO) < last_date

        return CloseReason(is_timeout=is_timeout, is_successful=is_successful)
    

    def getStrategyType(self) -> StrategyType:
        return STRATEGY_TYPE
