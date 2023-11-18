import psycopg2
from typing import List
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from lppls_dataclasses import Suggestion
from lppls_defaults import DEFAULT_POSITION_SIZE, TOP_BUBBLE_CONFIDENCE_IN_PRACTICE
from datetime import datetime

STRATEGY_TYPE = "SORNETTE"

class TradeSuggestions:

    def create_if_not_exists(self, cursor) -> None:
        # Check and create ENUM types if they don't exist
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'strategy_type') THEN
                    CREATE TYPE strategy_type AS ENUM ('SORNETTE', 'TAO', 'ELECTION_ARB');
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_type') THEN
                    CREATE TYPE order_type AS ENUM ('BUY', 'SELL');
                END IF;
            END
            $$;
            """)

        # Create 'suggestions' table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            strategy_t strategy_type,
            order_t order_type,
            open_date DATE,
            open_price FLOAT,
            is_position_open BOOLEAN DEFAULT TRUE,
            close_date DATE,
            close_price FLOAT,
            ticker VARCHAR(10),
            confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
            position_size FLOAT,
            PRIMARY KEY (open_date, ticker, strategy_t),
            CHECK (
                (is_position_open AND close_price IS NULL) OR
                (NOT is_position_open AND close_price IS NOT NULL)
            )
        );
        """)
        print('created table suggestions')


    def is_position_open(self, cursor, ticker, strategy) -> bool:
        cursor.execute(
            """
            SELECT COUNT(*) FROM suggestions
            WHERE ticker = %s AND strategy_t = %s AND is_position_open = TRUE
            """,
            (ticker, strategy)
        )
        result = cursor.fetchone()
        return result[0] > 0


    def write_suggestions(self, suggestions: List[Suggestion]) -> None:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
        )
        cursor = conn.cursor()
        self.create_if_not_exists(cursor)

        for suggestion in suggestions:
            if self.is_position_open(cursor, suggestion.ticker, STRATEGY_TYPE):
                continue
    
            position_size = DEFAULT_POSITION_SIZE * suggestion.confidence / TOP_BUBBLE_CONFIDENCE_IN_PRACTICE
            formatted_open_date = datetime.fromordinal(suggestion.open_date).strftime("%Y-%m-%d")
            cursor.execute(
                """
                INSERT INTO suggestions (strategy_t, order_t, open_date, open_price, ticker, confidence, position_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                STRATEGY_TYPE,
                'SELL' if suggestion.bubble_type.POSITIVE else 'BUY',

                formatted_open_date,
                suggestion.price,

                suggestion.ticker,
                suggestion.confidence,
                position_size
            ))

        conn.commit()
        cursor.close()
        conn.close()
