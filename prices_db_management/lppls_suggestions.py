from typing import List
from db_dataclasses import Suggestion, ClosingPrices, OrderType, CloseReason
from db_defaults import DEFAULT_POSITION_SIZE, TOP_BUBBLE_CONFIDENCE_IN_PRACTICE
from datetime import date
from trade_suggestions import TradeSuggestions
from db_dataclasses import StrategyType
from datetime import timedelta
from date_utils import ordinal_to_date

STRATEGY_TYPE = StrategyType.SORNETTE

MAX_DAYS_AFTER_BUBBLE_POP_CLOSE_LPPLS = 30  # 1 month
CLOSE_THRESHOLD = 0.15  # 15%
STRATEGY_TYPE = StrategyType.SORNETTE


class LpplsSuggestions(TradeSuggestions):
    def maybe_insert_suggestions(self, suggestions: List[Suggestion], cursor) -> None:
        for suggestion in suggestions:
            if self.is_position_open(cursor, suggestion.ticker, STRATEGY_TYPE):
                continue

            position_size = (
                DEFAULT_POSITION_SIZE * suggestion.confidence / TOP_BUBBLE_CONFIDENCE_IN_PRACTICE
            )
            formatted_open_date = ordinal_to_date(suggestion.open_date)

            assert suggestion.pop_dates_range is not None
            formmated_pop_start = ordinal_to_date(suggestion.pop_dates_range.first_pop_date)
            formmated_pop_end = ordinal_to_date(suggestion.pop_dates_range.last_pop_date)
            cursor.execute(
                """
                INSERT INTO suggestions (strategy_t, order_t, open_date, open_price, ticker, confidence, position_size, earliest_pop_date, latest_pop_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (open_date, ticker, strategy_t) DO NOTHING
            """,
                (
                    STRATEGY_TYPE.value,
                    suggestion.order_type.value,
                    formatted_open_date,
                    suggestion.price,
                    suggestion.ticker,
                    suggestion.confidence,
                    position_size,
                    formmated_pop_start,
                    formmated_pop_end,
                ),
            )

    def maybe_close(
        self, order_type: OrderType, ticker: str, open_date: date, last_date: date, cursor
    ) -> CloseReason:
        cursor.execute(
            """
            SELECT latest_pop_date
            FROM suggestions 
            WHERE strategy_t = 'SORNETTE' AND is_position_open = TRUE AND ticker = %s;
        """,
            (ticker,),
        )
        latest_pop_date = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT date, ticker, close_price, high_price, low_price FROM pricing_history
            WHERE ticker = %s
            AND date >= %s
            ORDER BY date;
        """,
            (ticker, open_date),
        )
        rows = cursor.fetchall()

        closing_prices = [
            ClosingPrices(close_price=row["close_price"], date=row["date"]) for row in rows
        ]

        last_price = closing_prices[-1].close_price

        if order_type == OrderType.BUY:
            min_price = max(closing_prices, key=lambda price: price.close_price).close_price
            profit = (last_price - min_price) / min_price
        elif order_type == OrderType.SELL:
            max_price = max(closing_prices, key=lambda price: price.close_price).close_price
            profit = -1 * (last_price - max_price) / max_price
        else:
            raise Exception("Invalid order type")

        is_successful = profit >= CLOSE_THRESHOLD
        is_timeout = (
            latest_pop_date + timedelta(days=MAX_DAYS_AFTER_BUBBLE_POP_CLOSE_LPPLS) < last_date
        )

        return CloseReason(is_timeout=is_timeout, is_successful=is_successful)

    def getStrategyType(self) -> StrategyType:
        return STRATEGY_TYPE
