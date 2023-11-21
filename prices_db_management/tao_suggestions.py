from typing import List
from db_dataclasses import Suggestion
from db_defaults import DEFAULT_POSITION_SIZE
from datetime import datetime
from trade_suggestions import TradeSuggestions


STRATEGY_TYPE = "TAO_RSI"


class TaoSuggestions(TradeSuggestions):
    def __init__(self):
        # Initialize the parent class
        super().__init__()


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
                STRATEGY_TYPE,
                suggestion.order_type.value,

                formatted_open_date,
                suggestion.price,

                suggestion.ticker,
                suggestion.confidence,
                DEFAULT_POSITION_SIZE
            ))
