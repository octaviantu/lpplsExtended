import psycopg2
from typing import List, Tuple
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from db_dataclasses import (
    Suggestion,
    StrategyResult,
    StrategyType,
    OrderType,
    CloseReason,
    ClosedPosition,
)
from abc import abstractmethod
from db_dataclasses import StrategyType
from psycopg2.extras import DictCursor
from typechecking import TypeCheckBase

STOP_LOS_THRESHOLD = -0.1  # 10%
# Over thit profit, we check if we should close. This is a minimum required to close.
# However, implementations of this class will have different criteria.
MIN_PROFIT_THREDHOLD = 0.05  # 5%


class TradeSuggestions(TypeCheckBase):
    def create_if_not_exists(self, cursor) -> None:
        # Check and create ENUM types if they don't exist
        cursor.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'strategy_type') THEN
                    CREATE TYPE strategy_type AS ENUM ('SORNETTE', 'TAO_RSI', 'ELECTION_ARB');
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_type') THEN
                    CREATE TYPE order_type AS ENUM ('BUY', 'SELL');
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'close_reason') THEN
                    CREATE TYPE close_reason AS ENUM ('VALUE_INCREASE', 'KELTNER CHANNELS', 'TIMEOUT');
                END IF;
            END
            $$;
            """
        )

        # Create 'suggestions' table if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS suggestions (
                strategy_t strategy_type,
                order_t order_type,
                open_date DATE,
                open_price FLOAT,
                is_position_open BOOLEAN DEFAULT TRUE,
                close_date DATE,
                earliest_pop_date DATE,
                latest_pop_date DATE,
                close_price FLOAT,
                close_reason close_reason,
                ticker VARCHAR(10),
                confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
                position_size FLOAT,
                PRIMARY KEY (open_date, ticker, strategy_t),
                CHECK (
                    (is_position_open AND close_price IS NULL) OR
                    (NOT is_position_open AND close_price IS NOT NULL)
                ),
                CHECK (
                    (strategy_t != 'SORNETTE' AND earliest_pop_date IS NULL AND latest_pop_date IS NULL) OR 
                    (strategy_t = 'SORNETTE' AND earliest_pop_date IS NOT NULL AND latest_pop_date IS NOT NULL)
                )
            );
        """
        )

    def is_position_open(self, cursor, ticker, strategy_type: StrategyType) -> bool:
        cursor.execute(
            """
            SELECT COUNT(*) FROM suggestions
            WHERE ticker = %s AND strategy_t = %s AND is_position_open = TRUE
            """,
            (ticker, strategy_type.value),
        )
        result = cursor.fetchone()
        return result[0] > 0

    def write_suggestions(self, suggestions: List[Suggestion]) -> None:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
        )
        cursor = conn.cursor()
        self.create_if_not_exists(cursor)

        self.maybe_insert_suggestions(suggestions, cursor)

        conn.commit()
        cursor.close()
        conn.close()

    @abstractmethod
    def maybe_insert_suggestions(self, suggestions: List[Suggestion], cursor) -> None:
        pass

    def score_previous_suggestions(self, conn, test_date: str) -> StrategyResult:
        conn.cursor_factory = DictCursor
        cursor = conn.cursor()

        STRATEGY_TYPE = self.getStrategyType()

        # Query to get all TAO_RSI suggestions that are open
        cursor.execute(
            """
            SELECT ticker, open_price, position_size, order_t, open_date
            FROM suggestions 
            WHERE strategy_t = %s AND is_position_open = TRUE AND open_date <= %s;
        """,
            (STRATEGY_TYPE.value, test_date),
        )
        suggestions = cursor.fetchall()

        STRATEGY_TYPE = self.getStrategyType()
        closed_positions = []

        for suggestion in suggestions:
            ticker = suggestion["ticker"]
            open_price = suggestion["open_price"]
            position_size = suggestion["position_size"]
            order_type = OrderType[suggestion["order_t"]]
            open_date = str(suggestion["open_date"])

            # Query to get the latest price from pricing_history
            cursor.execute(
                """
                SELECT date, close_price FROM pricing_history
                WHERE date = (
                    SELECT MAX(date) FROM pricing_history WHERE date < %s
                )
                AND ticker = %s;
            """,
                (test_date, ticker),
            )
            row = cursor.fetchone()
            if not row:
                continue

            last_date, last_close_price = str(row[0]), row[1]

            sign = 1 if order_type == OrderType.BUY else -1
            profit = ((last_close_price - open_price) / open_price) * sign

            close_reason = None
            if profit <= STOP_LOS_THRESHOLD:
                close_reason = CloseReason.STOP_LOSS
            elif profit >= MIN_PROFIT_THREDHOLD:
                # Check conditions to close the position
                close_reason = self.maybe_close(order_type, ticker, open_date, last_date, cursor)

            if close_reason:
                closed_positions.append(
                    ClosedPosition(
                        ticker=ticker,
                        open_date=open_date,
                        open_price=open_price,
                        close_date=last_date,
                        close_price=last_close_price,
                        position_size=position_size,
                        strategy_type=STRATEGY_TYPE,
                        close_reason=close_reason,
                        order_type=order_type,
                    )
                )

                # Update the suggestion
                cursor.execute(
                    """
                    UPDATE suggestions SET 
                    is_position_open = FALSE, 
                    close_date = %s,
                    close_price = %s,
                    close_reason = %s
                    WHERE open_date = %s AND ticker = %s AND strategy_t = %s;
                """,
                    (
                        last_date,
                        last_close_price,
                        close_reason.value,
                        open_date,
                        ticker,
                        STRATEGY_TYPE.value,
                    ),
                )
                conn.commit()

        paid, received, succesful_count, timeout_count, stop_loss_count = self.aggregate_counts(
            closed_positions
        )

        strategy_results = StrategyResult(
            strategy_type=STRATEGY_TYPE,
            succesful_count=succesful_count,
            timeout_count=timeout_count,
            stop_loss_count=stop_loss_count,
            paid=paid,
            received=received,
            closed_positions=closed_positions,
        )

        # Close the cursor and the connection
        cursor.close()

        return strategy_results

    def fetch_all_closed_suggestions(self, conn) -> StrategyResult:
        conn.cursor_factory = DictCursor
        cursor = conn.cursor()

        STRATEGY_TYPE = self.getStrategyType()

        # Query to get all TAO_RSI suggestions that are open
        cursor.execute(
            """
            SELECT ticker, open_price, position_size, order_t, open_date, close_date, close_price, close_reason
            FROM suggestions 
            WHERE strategy_t = %s AND is_position_open = FALSE
            ORDER BY open_date, close_date, ticker;
        """,
            (STRATEGY_TYPE.value,),
        )
        suggestions = cursor.fetchall()

        STRATEGY_TYPE = self.getStrategyType()
        closed_positions = []

        for suggestion in suggestions:
            ticker = suggestion["ticker"]
            open_price = suggestion["open_price"]
            position_size = suggestion["position_size"]
            order_type = OrderType[suggestion["order_t"]]
            open_date = str(suggestion["open_date"])
            last_date = str(suggestion["close_date"])
            close_price = suggestion["close_price"]
            close_reason = CloseReason[suggestion["close_reason"]]

            closed_positions.append(
                ClosedPosition(
                    ticker=ticker,
                    open_date=open_date,
                    open_price=open_price,
                    close_date=last_date,
                    close_price=close_price,
                    position_size=position_size,
                    strategy_type=STRATEGY_TYPE,
                    close_reason=close_reason,
                    order_type=order_type,
                )
            )

        # Close the cursor and the connection
        cursor.close()

        paid, received, succesful_count, timeout_count, stop_loss_count = self.aggregate_counts(
            closed_positions
        )

        return StrategyResult(
            strategy_type=STRATEGY_TYPE,
            succesful_count=succesful_count,
            timeout_count=timeout_count,
            stop_loss_count=stop_loss_count,
            paid=paid,
            received=received,
            closed_positions=closed_positions,
        )

    @abstractmethod
    def maybe_close(
        self, order_type: OrderType, ticker: str, open_date: int, last_date: int, cursor
    ) -> CloseReason | None:
        pass

    @abstractmethod
    def getStrategyType(self) -> StrategyType:
        pass

    def aggregate_counts(
        self, closed_positions: List[ClosedPosition]
    ) -> Tuple[float, float, int, int, int]:
        paid = 0.0
        received = 0.0
        succesful_count = 0
        timeout_count = 0
        stop_loss_count = 0

        closed_positions = sorted(closed_positions, key=lambda x: (x.close_date, x.ticker))
        for closed_position in closed_positions:
            open_price = closed_position.open_price
            position_size = closed_position.position_size
            order_type = closed_position.order_type
            close_price = closed_position.close_price
            close_reason = closed_position.close_reason

            if not close_reason:
                continue
            if close_reason == CloseReason.TIMEOUT:
                timeout_count += 1
            elif close_reason == CloseReason.STOP_LOSS:
                stop_loss_count += 1
            elif close_reason in [CloseReason.KELTNER_CHANNELS, CloseReason.VALUE_INCREASE]:
                succesful_count += 1
            else:
                raise Exception("Invalid close reason")

            if order_type == OrderType.BUY:
                paid += position_size
                received += close_price * (position_size / open_price)
            else:
                paid += close_price * (position_size / open_price)
                received += position_size

        return paid, received, succesful_count, timeout_count, stop_loss_count
