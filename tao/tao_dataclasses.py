from dataclasses import dataclass
from typing import List

ATR_RANGE = 20
ATR_BAND_NR_PROFIT = 2

MAX_DAYS_UNTIL_CLOSE_POSITION_TAO = 3 * 30  # 3 months


@dataclass
class PriceData:
    date_ordinal: int
    ticker: str
    close_price: float
    high_price: float
    low_price: float


@dataclass
class TipTechnicalData:
    ema_8: float
    ema_21: float
    ema_34: float
    ema_55: float
    ema_89: float
    slow_stoch_d: float
    adx: float
    rsi_yesterday: float
    rsi_today: float


@dataclass
class FullTechnicalData:
    ema_8: List[float]
    ema_21: List[float]
    ema_34: List[float]
    ema_55: List[float]
    ema_89: List[float]
    slow_stoch_d: List[float]
    adx: List[float]
    rsi: List[float]
