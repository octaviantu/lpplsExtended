from enum import Enum
from dataclasses import dataclass
from lppls_defaults import BubbleType


@dataclass
class Suggestion:
    bubble_type: BubbleType
    ticker: str
    confidence: float
    price: float
    open_date: int
    close_date: int
