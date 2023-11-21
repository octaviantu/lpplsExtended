from typing import List
from db_dataclasses import Suggestion, StrategyResults, StrategyType, OrderType
from db_defaults import DEFAULT_POSITION_SIZE
from datetime import datetime, timedelta
from trade_suggestions import TradeSuggestions
import numpy as np
from price_technicals import PriceTechnicals
from tao_dataclasses import MAX_DAYS_UNTIL_CLOSE_POSITION

STRATEGY_TYPE = StrategyType.TAO_RSI


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
                STRATEGY_TYPE.value,
                suggestion.order_type.value,

                formatted_open_date,
                suggestion.price,

                suggestion.ticker,
                suggestion.confidence,
                DEFAULT_POSITION_SIZE
            ))


    def score_previous_suggestions(self, conn) -> TradeSuggestions:
        cursor = conn.cursor()
        
        # Query to get all TAO_RSI suggestions that are open
        cursor.execute("""
            SELECT * FROM suggestions 
            WHERE strategy_t = 'TAO_RSI' AND is_position_open = TRUE;
        """)
        suggestions = cursor.fetchall()
        
        # Query to get the latest date from pricing_history
        cursor.execute("""
            SELECT MAX(date) FROM pricing_history;
        """)
        latest_date = cursor.fetchone()[0]
        
        investment_sum = 0
        final_sum = 0
        trade_count = 0

        price_technicals = PriceTechnicals()

        for suggestion in suggestions:
            ticker = suggestion['ticker']
            open_price = suggestion['open_price']
            position_size = suggestion['position_size']
            order_type = OrderType[suggestion['order_t']]


            trade_count += 1  # Increment the count of trades
            investment_sum += open_price * position_size
            final_sum += close_price * position_size

            # Get pricing data for the ticker
            cursor.execute("""
                SELECT * FROM pricing_history
                WHERE ticker = %s ORDER BY date DESC LIMIT 21;
            """, (ticker,))
            pricing_data = cursor.fetchall()
            
            # Calculate 21-day mean and 2ATR
            mean_price = np.mean([data['close_price'] for data in pricing_data])
            atr = price_technicals.calculate_atr(pricing_data)[-1]  # You should implement this method

            # Check conditions to close the position
            if (price_technicals.is_outside_atr_band(open_price, mean_price, atr, order_type) or 
                suggestion['open_date'] + timedelta(days=MAX_DAYS_UNTIL_CLOSE_POSITION) < latest_date):

                close_price = pricing_data[0]['close_price']
                total_score += (close_price - open_price) * position_size
                
                # Update the suggestion
                cursor.execute("""
                    UPDATE suggestions SET 
                    is_position_open = FALSE, 
                    close_date = %s ,
                    close_price = %s
                    WHERE open_date = %s AND ticker = %s AND strategy_t = 'TAO_RSI';
                """, (latest_date, close_price, suggestion['open_date'], ticker))
                conn.commit()


        strategy_results = StrategyResults(
            strategy_type=STRATEGY_TYPE,
            trade_count=trade_count,
            investment_sum=investment_sum,
            final_sum=final_sum
        )
                
        # Close the cursor and the connection
        cursor.close()
        
        return strategy_results
