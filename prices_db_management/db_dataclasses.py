from enum import Enum
from dataclasses import dataclass
from typing import List


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class StrategyType(Enum):
    SORNETTE = "SORNETTE"
    TAO_RSI = "TAO_RSI"


class CloseReason(Enum):
    TIMEOUT = "TIMEOUT"
    SUCCESS = "SUCCESS"


@dataclass
class PopRange:
    first_pop_date: int
    last_pop_date: int


@dataclass
class Suggestion:
    order_type: OrderType
    ticker: str
    confidence: float
    price: float
    open_date: int
    pop_dates_range: PopRange | None = None


@dataclass
class ClosedPosition:
    ticker: str
    open_date: int
    open_price: float
    close_date: int
    close_price: float
    position_size: float
    strategy_type: StrategyType
    close_reason: CloseReason
    order_type: OrderType

    def compute_profit_percent(self) -> str:
        if self.open_price == 0.0:
            return 0.0
        profit = 100 * (self.close_price - self.open_price) / self.open_price
        sign = 1 if self.order_type == OrderType.BUY else -1
        return f'{round(sign *profit, 2)}%'

    def compute_profit_absolute(self) -> float:
        abs_sum = (self.close_price * (self.position_size / self.open_price)) - self.position_size
        sign = 1 if self.order_type == OrderType.BUY else -1
        return sign * abs_sum


@dataclass
class StrategyResult:
    strategy_type: StrategyType
    succesful_count: int
    timeout_count: int
    paid: float
    received: float
    closed_positions: List[ClosedPosition]

    def compute_profit_percent(self) -> str:
        if self.paid == 0.0:
            return '0%'
        profit = 100 * (self.received - self.paid) / self.paid
        return f'{round(profit, 2)}%'
    
    def compute_profit_absolute(self) -> float:
        return self.received - self.paid

    def compute_trade_count(self) -> int:
        return self.succesful_count + self.timeout_count
