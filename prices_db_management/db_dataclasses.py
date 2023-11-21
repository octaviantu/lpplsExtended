from enum import Enum
from typing import Tuple
from dataclasses import dataclass


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class StrategyType(Enum):
    SORNETTE = "SORNETTE"
    TAO_RSI = "TAO_RSI"

@dataclass
class Suggestion:
    order_type: OrderType
    ticker: str
    confidence: float
    price: float
    open_date: int
    pop_dates_range: Tuple[int, int] = Tuple[None, None]


@dataclass
class StrategyResults:
    strategy_type: str
    trade_count: int
    investment_sum: float
    final_sum: float

    def getProfit(self) -> float:
        return (self.final_sum - self.investment_sum) / self.investment_sum