from starts import Starts
from lppls_defaults import BubbleStart
import pandas as pd
from typing import List

class Bounds:

    def __init__(self):
        self.starts = Starts()

    def compute_start_time(self, dates: List[int], actual_prices, expected_prices, bubble_type, extremities) -> BubbleStart:
        # "We impose the constraint that, for a given developingbubble, its start time t1*
        # cannot be earlier than the previous peak, as determined in Figure 1.""
        # 
        # Dissection of Bitcoin’s Multiscale Bubble History from January 2012 to February 2018
        last_extremity_index = 0
        if len(extremities) > 0:
            last_extremity_index = dates.index(max(extremities.keys()))
        ssrn_lgrn, _ = self.starts.getLagrangeScore(actual_prices[last_extremity_index:], expected_prices[last_extremity_index:])

        min_index = last_extremity_index + ssrn_lgrn.index(min(ssrn_lgrn))
        return BubbleStart(pd.Timestamp.fromordinal(dates[min_index]), bubble_type)
