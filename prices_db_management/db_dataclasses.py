from enum import Enum
from typing import Tuple
from dataclasses import dataclass


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Suggestion:
    order_type: OrderType
    ticker: str
    confidence: float
    price: float
    open_date: int
    pop_dates_range: Tuple[int, int] = Tuple[None, None]
