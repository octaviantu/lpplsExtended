from typing import List
from db_dataclasses import Suggestion
from db_defaults import DEFAULT_POSITION_SIZE, TOP_BUBBLE_CONFIDENCE_IN_PRACTICE
from datetime import datetime
from trade_suggestions import TradeSuggestions


STRATEGY_TYPE = "SORNETTE"


class SornetteSuggestions(TradeSuggestions):
    def __init__(self):
        # Initialize the parent class
        super().__init__()


    def maybe_insert_suggestions(self, suggestions: List[Suggestion], cursor) -> None:
        for suggestion in suggestions:
            if self.is_position_open(cursor, suggestion.ticker, STRATEGY_TYPE):
                continue

            position_size = DEFAULT_POSITION_SIZE * suggestion.confidence / TOP_BUBBLE_CONFIDENCE_IN_PRACTICE
            formatted_open_date = datetime.fromordinal(suggestion.open_date).strftime("%Y-%m-%d")
            cursor.execute(
                """
                INSERT INTO suggestions (strategy_t, order_t, open_date, open_price, ticker, confidence, position_size, earliest_pop_date, latest_pop_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (open_date, ticker, strategy_t) DO NOTHING
            """, (
                STRATEGY_TYPE,
                suggestion.order_type,

                formatted_open_date,
                suggestion.price,

                suggestion.ticker,
                suggestion.confidence,
                position_size,
                suggestion.pop_dates_range[0],
                suggestion.pop_dates_range[1]
            ))