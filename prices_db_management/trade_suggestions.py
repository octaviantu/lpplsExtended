import psycopg2
from typing import List
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from db_dataclasses import Suggestion, StrategyResults, StrategyType, OrderType, CloseReason
from abc import abstractmethod
from db_dataclasses import StrategyType
from psycopg2.extras import DictCursor
from datetime import date


class TradeSuggestions:
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

    def score_previous_suggestions(self, conn) -> StrategyResults:
        conn.cursor_factory = DictCursor
        cursor = conn.cursor()

        STRATEGY_TYPE = self.getStrategyType()

        # Query to get all TAO_RSI suggestions that are open
        cursor.execute(
            """
            SELECT ticker, open_price, position_size, order_t, open_date
            FROM suggestions 
            WHERE strategy_t = %s AND is_position_open = TRUE;
        """,
            (STRATEGY_TYPE.value,),
        )
        suggestions = cursor.fetchall()

        # Query to get the latest date from pricing_history
        cursor.execute(
            """
            SELECT date, close_price FROM pricing_history
            WHERE date = (SELECT MAX(date) FROM pricing_history)
        """
        )
        result = cursor.fetchone()
        last_date, last_close_price = result

        paid = 0.0
        received = 0.0
        succesful_count = 0
        timeout_count = 0
        STRATEGY_TYPE = self.getStrategyType()

        for suggestion in suggestions:
            ticker = suggestion["ticker"]
            open_price = suggestion["open_price"]
            position_size = suggestion["position_size"]
            order_type = OrderType[suggestion["order_t"]]
            open_date = suggestion["open_date"]

            # Check conditions to close the position
            closeReason = self.maybe_close(order_type, ticker, open_date, last_date, cursor)
            is_timeout, is_successful = closeReason.is_timeout, closeReason.is_successful

            if is_successful:
                succesful_count += 1
            elif is_timeout:
                timeout_count += 1

            if is_timeout or is_successful:
                close_sum = (last_close_price / open_price) * position_size

                if order_type == OrderType.BUY:
                    paid += position_size
                    received += close_sum
                else:
                    paid += close_sum
                    received += position_size

                # Update the suggestion
                cursor.execute(
                    """
                    UPDATE suggestions SET 
                    is_position_open = FALSE, 
                    close_date = %s ,
                    close_price = %s
                    WHERE open_date = %s AND ticker = %s AND strategy_t = %s;
                """,
                    (last_date, last_close_price, open_date, ticker, STRATEGY_TYPE.value),
                )
                conn.commit()

        strategy_results = StrategyResults(
            strategy_type=STRATEGY_TYPE,
            succesful_count=succesful_count,
            timeout_count=timeout_count,
            paid=paid,
            received=received,
        )

        # Close the cursor and the connection
        cursor.close()

        return strategy_results

    @abstractmethod
    def maybe_close(
        self, order_type: OrderType, ticker: str, open_date: date, last_date: date, cursor
    ) -> CloseReason:
        pass

    @abstractmethod
    def getStrategyType(self) -> StrategyType:
        pass
