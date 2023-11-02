import numpy as np
import pandas as pd
from typing import List, Set
from collections import defaultdict


class Peaks:
    def __init__(self):
        self.D = 0.85
        self.epsilon_range = np.arange(0.1, 5.1, 0.1)
        self.w_range = np.arange(10, 61, 5)
        self.N_epsilon = len(self.epsilon_range) * len(self.w_range)


    def find_drawups(self, closing_prices: pd.DataFrame) -> List[int]:
        # We add a dummy first element to maintain the same index.
        log_returns = [0]
        for i in range(1, len(closing_prices)):
            log_returns.append(np.log(closing_prices["Adj Close"][i]) - np.log(closing_prices["Adj Close"][i - 1]))

        peak_times_counter = defaultdict(float)
        # For each window size, we calculate epsilon and then run the epsilon_drawup_drawdown
        for w in self.w_range:
            for epsilon_0 in self.epsilon_range:
                peaks = self.epsilon_drawups(epsilon_0, log_returns, closing_prices)
                for peak in peaks:
                    peak_times_counter[peak] += 1
        
        selected_peaks = dict()
        for peak in peak_times_counter:
            freq = peak_times_counter[peak] / self.N_epsilon
            if freq >= self.D:
                selected_peaks[peak] = freq

        return selected_peaks


    def epsilon_drawups(self, epsilon_0: float, log_returns: np.ndarray, closing_prices: pd.DataFrame) -> Set[pd.Timestamp]:
        peak_times = set()
        max_cum_return = 0
        cum_return = 0
        current_peak = 0

        for w in self.w_range:
            vol = np.std(log_returns[0:w])
            window_sum = np.sum(log_returns[0:w])
            window_sq_sum = sum(x ** 2 for x in log_returns[0:w])

            for i in range(0, len(log_returns)):
                # Optimised to reduce complexity and avoid computing vol for each iteration
                if i > w:
                    # Remove the oldest value from the sum and sum of squares
                    window_sum -= log_returns[i-w]
                    window_sq_sum -= log_returns[i-w] ** 2

                    # Add the new value to the sum and sum of squares
                    window_sum += log_returns[i]
                    window_sq_sum += log_returns[i] ** 2

                    # Calculate the new variance and standard deviation
                    mean = window_sum / w
                    variance = (window_sq_sum / w) - (mean ** 2)
                    vol = np.sqrt(variance)

                epsilon = epsilon_0 * vol

                cum_return += log_returns[i]
                if cum_return > max_cum_return:
                    max_cum_return = cum_return
                    current_peak = i
                
                deviation = max_cum_return - cum_return

                if deviation > epsilon:
                    # End of drawup phase, register the peak time
                    peak_time_index = current_peak
                    peak_times.add(closing_prices["Date"].iloc[peak_time_index])
                    max_cum_return = 0  # Reset for the new drawup phase
                    cum_return = 0

        return peak_times
