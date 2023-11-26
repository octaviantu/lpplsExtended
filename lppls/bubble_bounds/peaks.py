import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from collections import defaultdict
from lppls_dataclasses import BubbleType, Peak, ObservationSeries
from lppls_defaults import (
    EPSILON_RANGE_START,
    EPSILON_RANGE_END,
    EPSILON_STEP,
    PEAK_THRESHOLD,
    W_RANGE_END,
    W_RANGE_START,
    W_STEP,
)
import matplotlib.pyplot as plt
from datetime import datetime
from date_utils import ordinal_to_date
import matplotlib.dates as mdates


class Peaks:
    def __init__(self, observations: ObservationSeries, ticker: str):
        self.D = PEAK_THRESHOLD
        self.epsilon_range = np.arange(
            EPSILON_RANGE_START, EPSILON_RANGE_END + EPSILON_STEP, EPSILON_STEP
        )
        self.w_range = np.arange(W_RANGE_START, W_RANGE_END + W_STEP, W_STEP)
        self.N_epsilon = len(self.epsilon_range) * len(self.w_range)
        self.observations = observations
        self.ticker = ticker

    def find_extremities(self, bubble_type: BubbleType) -> List[Peak]:
        log_returns: List[float] = self.observations.get_log_returns()

        peak_times_counter = self.count_extremities(log_returns, bubble_type)

        selected_peaks = []
        for peak in peak_times_counter:
            freq = peak_times_counter[peak] / self.N_epsilon
            if freq >= self.D:
                selected_peaks.append(Peak(bubble_type, peak, freq))

        return selected_peaks

    def count_extremities(
        self, log_returns: List[float], bubble_type: BubbleType
    ) -> Dict[int, int]:
        peak_times_counter: Dict[int, int] = defaultdict(int)
        peak_cum_return = 0.0
        cum_return = 0.0
        current_peak = 0

        for epsilon_0 in self.epsilon_range:
            for w in self.w_range:
                vol = np.std(log_returns[0:w])
                peak_cum_return = 0
                cum_return = 0
                current_peak = 0

                for i, current_log_return in enumerate(log_returns):
                    # Optimised to reduce complexity and avoid computing vol for each iteration
                    if i > w:
                        vol = np.std(log_returns[i - w : i])

                    epsilon = epsilon_0 * vol

                    cum_return += current_log_return
                    if bubble_type == BubbleType.POSITIVE:
                        if cum_return > peak_cum_return:
                            peak_cum_return = cum_return
                            current_peak = i
                        deviation = peak_cum_return - cum_return
                    else:
                        if cum_return < peak_cum_return:
                            peak_cum_return = cum_return
                            current_peak = i
                        deviation = cum_return - peak_cum_return

                    if deviation > epsilon:
                        # End of drawup phase, register the peak time
                        peak_time_index = current_peak
                        peak_date = self.observations.get_date_at_ordinal(peak_time_index)
                        peak_times_counter[peak_date] += 1
                        peak_cum_return = 0  # Reset for the new drawup phase
                        cum_return = 0
                        current_peak = i + 1

        return peak_times_counter

    def plot_peaks(self) -> Tuple[List[Peak], List[Peak], str]:
        # Find drawups and drawdowns
        drawups = self.find_extremities(BubbleType.POSITIVE)
        drawdowns = self.find_extremities(BubbleType.NEGATIVE)

        # Create subplots for drawups and drawdowns
        today_date = datetime.today().strftime("%Y-%m-%d")
        image_name = f"{self.ticker} on {today_date}"
        fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(14, 10))
        fig.canvas.manager.set_window_title(image_name)

        formtted_dates = self.observations.get_formatted_dates()

        prices = self.observations.get_prices()
        # Get the maximum price to determine the top of the graph
        max_price = max(prices)

        ax1.plot(formtted_dates, prices, label="Price", color="black", linewidth=0.75)
        for drawup in drawups:
            formatted_drawup_date = ordinal_to_date(drawup.date_ordinal)
            ax1.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
            ax1.axvline(x=formatted_drawup_date, color="red", linewidth=0.5)
            ax1.text(
                formatted_drawup_date,
                max_price,
                f"{formatted_drawup_date}({drawup.score:.2f})",
                color="red",
                rotation=90,
                verticalalignment="top",
                horizontalalignment="right",
            )

        ax1.set_title("Drawups")

        ax2.plot(formtted_dates, prices, label="Price", color="black", linewidth=0.75)
        for drawdown in drawdowns:
            formatted_drawdown_date = ordinal_to_date(drawdown.date_ordinal)
            ax2.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
            ax2.axvline(x=formatted_drawdown_date, color="green", linewidth=0.5)
            ax2.text(
                formatted_drawdown_date,
                max_price,
                f"{formatted_drawdown_date}({drawdown.score:.2f})",
                color="green",
                rotation=90,
                verticalalignment="top",
                horizontalalignment="right",
            )

        ax2.set_title("Drawdowns")

        return drawups, drawdowns, image_name
