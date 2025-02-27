from typing import List
from prices_db_management.db_dataclasses import Suggestion, StrategyType, OrderType, CloseReason
from tao.tao_dataclasses import ATR_RANGE
from prices_db_management.db_defaults import DEFAULT_POSITION_SIZE
from prices_db_management.trade_suggestions import TradeSuggestions
from tao.price_technicals import PriceTechnicals
from tao.tao_dataclasses import PriceData, MAX_DAYS_UNTIL_CLOSE_POSITION_TAO
from common.date_utils import DateUtils as du

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

            formatted_open_date = du.ordinal_to_date(suggestion.open_date)
            cursor.execute(
                """
                INSERT INTO suggestions (strategy_t, order_t, open_date, open_price, ticker, confidence, position_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (open_date, ticker, strategy_t) DO NOTHING
            """,
                (
                    STRATEGY_TYPE.value,
                    suggestion.order_type.value,
                    formatted_open_date,
                    suggestion.price,
                    suggestion.ticker,
                    suggestion.confidence,
                    DEFAULT_POSITION_SIZE,
                ),
            )

    def maybe_close(
        self, order_type: OrderType, ticker: str, open_date: str, _open_price: float, last_date: str,
        _last_price: float, cursor
    ) -> CloseReason | None:
        # Get pricing data for the ticker
        cursor.execute(
            """
            SELECT sub.date, sub.ticker, sub.close_price, sub.high_price, sub.low_price
            FROM (
                SELECT date, ticker, close_price, high_price, low_price
                FROM pricing_history
                WHERE ticker = %s
                AND date < %s
                ORDER BY date DESC
                LIMIT %s
            ) AS sub
            ORDER BY sub.date ASC;
        """,
            (ticker, last_date, ATR_RANGE + 1),
        )
        rows = cursor.fetchall()

        pricing_data = [
            PriceData(
                date_ordinal=du.date_to_ordinal(row["date"]),
                ticker=row["ticker"],
                close_price=row["close_price"],
                high_price=row["high_price"],
                low_price=row["low_price"],
            )
            for row in rows
        ]

        if self.price_technicals.is_outside_atr_band(pricing_data, order_type):
            return CloseReason.KELTNER_CHANNELS
        elif du.date_to_ordinal(open_date) + MAX_DAYS_UNTIL_CLOSE_POSITION_TAO < du.date_to_ordinal(
            last_date
        ):
            return CloseReason.TIMEOUT
        return None

    def getStrategyType(self) -> StrategyType:
        return STRATEGY_TYPE
