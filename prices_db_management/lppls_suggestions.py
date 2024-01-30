from typing import List
from prices_db_management.db_dataclasses import Suggestion, OrderType, CloseReason
from prices_db_management.db_defaults import (
    DEFAULT_POSITION_SIZE,
    TOP_BUBBLE_CONFIDENCE_IN_PRACTICE,
)
from prices_db_management.trade_suggestions import TradeSuggestions
from prices_db_management.db_dataclasses import StrategyType
from common.date_utils import DateUtils as du
from prices_db_management.prices_utils import compute_profit

STRATEGY_TYPE = StrategyType.SORNETTE

MAX_DAYS_AFTER_BUBBLE_POP_CLOSE_LPPLS = 30  # 1 month
CLOSE_THRESHOLD_LPPLS = 0.10  # 10%
STRATEGY_TYPE = StrategyType.SORNETTE


class LpplsSuggestions(TradeSuggestions):
    def maybe_insert_suggestions(self, suggestions: List[Suggestion], cursor) -> None:
        for suggestion in suggestions:
            position_size = (
                DEFAULT_POSITION_SIZE * suggestion.confidence / TOP_BUBBLE_CONFIDENCE_IN_PRACTICE
            )
            formatted_open_date = du.ordinal_to_date(suggestion.open_date)

            assert suggestion.pop_dates_range is not None
            formmated_pop_start = du.ordinal_to_date(suggestion.pop_dates_range.first_pop_date)
            formmated_pop_end = du.ordinal_to_date(suggestion.pop_dates_range.last_pop_date)

            cursor.execute(
                """
                INSERT INTO lppls_suggestions_pop_times (ticker, open_date, order_t, earliest_pop_date, latest_pop_date)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (ticker, open_date, order_t) DO NOTHING
            """,
                (
                    suggestion.ticker,
                    formatted_open_date,
                    suggestion.order_type.value,
                    formmated_pop_start,
                    formmated_pop_end,
                ),
            )

            if self.is_position_open(cursor, suggestion.ticker, STRATEGY_TYPE):
                cursor.execute(
                    """
                    UPDATE suggestions
                    SET daily_runs_count = daily_runs_count + 1
                    WHERE ticker = %s AND strategy_t = %s AND is_position_open = TRUE
                    """,
                    (suggestion.ticker, STRATEGY_TYPE.value),
                )
                continue

            cursor.execute(
                """
                INSERT INTO suggestions (strategy_t, order_t, open_date, open_price, ticker, confidence, position_size, earliest_pop_date, latest_pop_date, daily_runs_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    1,
                ),
            )

    def maybe_close(
        self, order_type: OrderType, ticker: str, _open_date: str, open_price: float, last_date: str,
        last_price: float, cursor
    ) -> CloseReason | None:
        cursor.execute(
            """
            SELECT latest_pop_date
            FROM suggestions 
            WHERE strategy_t = 'SORNETTE' AND is_position_open = TRUE AND ticker = %s;
        """,
            (ticker,),
        )
        latest_pop_date = str(cursor.fetchone()[0])

        profit = compute_profit(order_type, open_price, last_price)
        if profit >= CLOSE_THRESHOLD_LPPLS:
            return CloseReason.VALUE_INCREASE
        if du.date_to_ordinal(
            latest_pop_date
        ) + MAX_DAYS_AFTER_BUBBLE_POP_CLOSE_LPPLS < du.date_to_ordinal(last_date):
            return CloseReason.TIMEOUT
        return None

    def getStrategyType(self) -> StrategyType:
        return STRATEGY_TYPE
