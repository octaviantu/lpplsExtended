from typing import Tuple
from dataclasses import dataclass
from lppls_defaults import BubbleType


@dataclass
class Suggestion:
    bubble_type: BubbleType
    ticker: str
    confidence: float
    price: float
    open_date: int
    pop_dates_range: Tuple[int, int] = Tuple[None, None]
