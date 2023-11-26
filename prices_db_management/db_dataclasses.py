from enum import Enum
from dataclasses import dataclass


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class StrategyType(Enum):
    SORNETTE = "SORNETTE"
    TAO_RSI = "TAO_RSI"


@dataclass
class CloseReason:
    is_timeout: bool
    is_successful: bool


@dataclass
class ClosingPrices:
    close_price: float
    date: int


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
class StrategyResults:
    strategy_type: StrategyType
    succesful_count: int
    timeout_count: int
    paid: float
    received: float

    def compute_profit(self) -> float:
        if self.paid == 0.0:
            return 0.0
        return (self.received - self.paid) / self.paid

    def compute_trade_count(self) -> int:
        return self.succesful_count + self.timeout_count
