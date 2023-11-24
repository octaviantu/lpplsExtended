from typing import Dict, Tuple
import numpy as np
from lppls_math import LPPLSMath
from tqdm import tqdm
import pandas as pd
from matplotlib import pyplot as plt
from multiprocessing import Pool
from lppls_defaults import LARGEST_WINDOW_SIZE, SMALLEST_WINDOW_SIZE, T1_STEP, T2_STEP, MAX_SEARCHES
from lppls_dataclasses import BubbleStart, ObservationSeries
from filter_interface import FilterInterface
import sys


class DataFit:
    def __init__(self, observations: ObservationSeries, filter: FilterInterface):
        self.observations = observations
        self.filter = filter

    def plot_fit(
        self, bubble_start: BubbleStart, tc: float, m: float, w: float, a: float, b: float, c1: float, c2: float
    ) -> None:
        observations = self.observations.filter_before_tc(tc)

        if bubble_start is None:
            start_date = bubble_start.date_ordinal
            observations = observations.filter_between_date_ordinals(start_date)

        log_price_prediction = LPPLSMath.get_log_price_predictions(observations, tc, m, w, a, b, c1, c2)
        time_ord = observations.get_date_ordinals()

        _, (ax1) = plt.subplots(nrows=1, ncols=1, sharex=True, figsize=(14, 8))

        ax1.plot(time_ord, observations.get_log_prices(), label="price", color="black", linewidth=0.75)
        ax1.plot(time_ord, log_price_prediction, label="lppls fit", color="blue", alpha=0.5)

        # set grids
        ax1.grid(which="major", axis="both", linestyle="--")
        # set labels
        ax1.set_ylabel("ln(p)")
        ax1.legend(loc=2)

        plt.xticks(rotation=45)

    def fit(
        self, max_searches: int, observations: ObservationSeries, minimizer: str = "Nelder-Mead"
    ) -> Tuple[bool, Dict[str, float]]:
        return self.filter.fit(max_searches, observations, minimizer)

    def parallel_compute_t2_fits(self, **kwargs):
        return self.parallel_compute_t2_recent_fits(np.inf, **kwargs)

    def parallel_compute_t2_recent_fits(
        self,
        recent_windows,
        workers,
        window_size=LARGEST_WINDOW_SIZE,
        smallest_window_size=SMALLEST_WINDOW_SIZE,
        t1_increment=T1_STEP,
        t2_increment=T2_STEP,
        max_searches=MAX_SEARCHES,
    ):
        stop_windows_beginnings = len(self.observations) - window_size + 1
        start_windows_beginnings = max(
            len(self.observations) - window_size - recent_windows + 1, 0
        )

        t2_fits_args = []
        for i in range(start_windows_beginnings, stop_windows_beginnings, t2_increment):
            args = (
                self.observations.get_between_indexes(i, window_size + i),
                window_size,
                i,
                smallest_window_size,
                t1_increment,
                max_searches,
            )
            t2_fits_args.append(args)

        lppls_fits = []
        with Pool(processes=workers) as pool:
            lppls_fits = list(
                tqdm(
                    pool.imap(self.compute_t1_fits, t2_fits_args),
                    total=len(t2_fits_args),
                    dynamic_ncols=True,
                    file=sys.stdout,
                    position=0,
                )
            )

        return lppls_fits

    def compute_t1_fits(self, args):
        obs, window_size, t1_index, smallest_window_size, t1_increment, max_searches = args

        window_delta = window_size - smallest_window_size

        windows = []

        t1 = obs[0].date_ordinal
        t2 = obs[-1].date_ordinal
        p2 = obs[-1].price

        # have to store two indexes because trading days don't map to calendar days
        t2_index = t1_index + len(obs) - 1

        # run n fits on the observation slice.
        for j in range(0, window_delta, t1_increment):
            obs_shrinking_slice = obs[j:window_size]

            success, params_dict = self.fit(max_searches, obs_shrinking_slice)

            if not success:
                continue

            nested_t1 = obs_shrinking_slice[0].date_ordinal
            nested_t2 = obs_shrinking_slice[-1].date_ordinal

            # Update params_dict with new key-value pairs
            params_dict.update(
                {
                    "t1_d": LPPLSMath.ordinal_to_date(nested_t1),
                    "t2_d": LPPLSMath.ordinal_to_date(nested_t2),
                    "t1": nested_t1,
                    "t2": nested_t2,
                }
            )

            # Append updated params_dict to windows
            windows.append(params_dict)

        return {
            "t1": t1,
            "t2": t2,
            "p2": p2,
            "windows": windows,
            "t1_index": t1_index,
            "t2_index": t2_index,
        }
