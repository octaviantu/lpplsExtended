from typing import List
from tao_dataclasses import PriceData, ATR_RANGE, ATR_BAND_NR_PROFIT
import numpy as np
from ta.trend import EMAIndicator
import pandas as pd
from db_dataclasses import OrderType


class PriceTechnicals:
    def calculate_atr(self, prices: List[PriceData]):
        tr_values = []
        atrs = []

        for i in range(1, len(prices)):
            high = prices[i].high_price
            low = prices[i].low_price
            close_previous = prices[i - 1].close_price

            tr = max(high - low, abs(high - close_previous), abs(low - close_previous))
            tr_values.append(tr)
            # Calculate ATR from the first data point to the current one
            if i >= ATR_RANGE:
                atrs.append(np.mean(tr_values[i - ATR_RANGE : i]))

        return atrs

    def is_outside_atr_band(self, prices: List[PriceData], positionType: OrderType) -> bool:
        closing_prices = [p.close_price for p in prices]
        # Calculate EMA
        last_ema_price = (
            EMAIndicator(pd.Series(closing_prices), window=ATR_RANGE).ema_indicator().iloc[-1]
        )

        # Calculate ATR for the last point
        last_atr = self.calculate_atr(prices)[-1]

        # Calculate the price boundary based on ATR
        upper_band = last_ema_price + ATR_BAND_NR_PROFIT * last_atr
        lower_band = last_ema_price - ATR_BAND_NR_PROFIT * last_atr

        # Check if the last close price is within the 2 ATR band
        if positionType == OrderType.BUY:
            return prices[-1].close_price >= upper_band
        else:
            return prices[-1].close_price <= lower_band
