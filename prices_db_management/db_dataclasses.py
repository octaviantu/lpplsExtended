from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class StrategyType(Enum):
    SORNETTE = "SORNETTE"
    TAO_RSI = "TAO_RSI"


class CloseReason(Enum):
    TIMEOUT = "TIMEOUT"
    KELTNER_CHANNELS = "KELTNER_CHANNELS"
    VALUE_INCREASE = "VALUE_INCREASE"
    STOP_LOSS = "STOP_LOSS"


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
    daily_runs_count: int

    def compute_profit_percent(self) -> str:
        if self.open_price == 0.0:
            return 0.0
        profit = 100 * (self.close_price - self.open_price) / self.open_price
        sign = 1 if self.order_type == OrderType.BUY else -1
        return f"{round(sign *profit, 2)}%"

    def compute_profit_absolute(self) -> float:
        abs_sum = (self.close_price * (self.position_size / self.open_price)) - self.position_size
        sign = 1 if self.order_type == OrderType.BUY else -1
        return sign * abs_sum

@dataclass
class AggregateClosedPositions:
    paid: float
    received: float
    succesful_count: int
    timeout_count: int
    stop_loss_count: int
    closed_positions: List[ClosedPosition]

@dataclass
class StrategyResult:
    strategy_type: StrategyType
    unfiltered_closed_positions: List[ClosedPosition]
    desired_recommendation_count: int = 1
    cache: Dict[int, AggregateClosedPositions] = field(default_factory=dict)

    def aggregate_counts(self) -> AggregateClosedPositions:
        if self.desired_recommendation_count in self.cache:
            return self.cache[self.desired_recommendation_count]

        paid = 0.0
        received = 0.0
        succesful_count = 0
        timeout_count = 0
        stop_loss_count = 0

        closed_positions = sorted(self.unfiltered_closed_positions, key=lambda x: (x.close_date, x.ticker))
        selected_positions = []
        for closed_position in closed_positions:
            if closed_position.daily_runs_count < self.desired_recommendation_count:
                continue

            selected_positions.append(closed_position)
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

        agg = AggregateClosedPositions(paid=paid, received=received, succesful_count=succesful_count,
                                        timeout_count=timeout_count, stop_loss_count=stop_loss_count,
                                        closed_positions=selected_positions)

        self.cache[self.desired_recommendation_count] = agg
        return agg


    def compute_profit_percent(self) -> str:
        agg = self.aggregate_counts()
        if agg.paid == 0.0:
            return "0%"
        profit = 100 * (agg.received - agg.paid) / agg.paid
        return f"{round(profit, 2)}%"


    def compute_profit_absolute(self) -> float:
        agg = self.aggregate_counts()
        return agg.received - agg.paid


    def compute_trade_count(self) -> int:
        agg = self.aggregate_counts()
        return agg.succesful_count + agg.timeout_count + agg.stop_loss_count
    
    def get_closed_positions(self) -> List[ClosedPosition]:
        agg = self.aggregate_counts()
        return agg.closed_positions
