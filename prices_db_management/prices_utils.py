from prices_db_management.db_dataclasses import OrderType

def compute_profit(order_type: OrderType, open_price: float, close_price: float) -> float:
    sign = 1 if order_type == OrderType.BUY else -1
    profit = ((close_price - open_price) / open_price) * sign
    return profit
