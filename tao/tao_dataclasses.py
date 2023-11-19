from dataclasses import dataclass

@dataclass
class PriceData:
    date: str
    ticker: str
    close_price: float

@dataclass
class TechnicalData:
    ema_8: float
    ema_21: float
    ema_34: float
    ema_55: float
    ema_89: float
    slow_stoch_d: float
    adx: float
    rsi_yesterday: float
    rsi_today: float
