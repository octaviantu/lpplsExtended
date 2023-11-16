from typing import Dict, Tuple
import numpy as np
from lppls_math import LPPLSMath
from tqdm import tqdm
import pandas as pd
from matplotlib import pyplot as plt
from multiprocessing import Pool
from lppls_defaults import LARGEST_WINDOW_SIZE, SMALLEST_WINDOW_SIZE, T1_STEP, T2_STEP, MAX_SEARCHES
from filter_interface import FilterInterface
import sys


class DataFit:
    def __init__(self, observations, filter: FilterInterface):
        self.observations = observations
        self.filter = filter

    def plot_fit(
        self, tc: float, m: float, w: float, a: float, b: float, c1: float, c2: float
    ) -> None:
        obs_up_to_tc = LPPLSMath.stop_observation_at_tc(self.observations, tc)
        time_ord = [pd.Timestamp.fromordinal(int(d)) for d in obs_up_to_tc[0]]

        [price_prediction, actual_prices] = LPPLSMath.get_log_price_predictions(
            obs_up_to_tc, tc, m, w, a, b, c1, c2
        )

        _, (ax1) = plt.subplots(nrows=1, ncols=1, sharex=True, figsize=(14, 8))

        ax1.plot(time_ord, actual_prices, label="price", color="black", linewidth=0.75)
        ax1.plot(time_ord, price_prediction, label="lppls fit", color="blue", alpha=0.5)

        # set grids
        ax1.grid(which="major", axis="both", linestyle="--")
        # set labels
        ax1.set_ylabel("ln(p)")
        ax1.legend(loc=2)

        plt.xticks(rotation=45)

    def fit(
        self, max_searches: int, obs: np.ndarray, minimizer: str = "Nelder-Mead"
    ) -> Tuple[bool, Dict[str, float]]:
        return self.filter.fit(max_searches, obs, minimizer)

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
        stop_windows_beginnings = len(self.observations[0]) - window_size + 1
        start_windows_beginnings = max(
            len(self.observations[0]) - window_size - recent_windows + 1, 0
        )

        obs_copy = self.observations
        t2_fits_args = []
        for i in range(start_windows_beginnings, stop_windows_beginnings, t2_increment):
            args = (
                obs_copy[:, i : window_size + i],
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

        t1 = obs[0][0]
        t2 = obs[0][-1]
        p1 = obs[1][0]
        p2 = obs[1][-1]

        # have to store two indexes because trading days don't map to calendar days
        t2_index = t1_index + len(obs[0]) - 1

        # run n fits on the observation slice.
        for j in range(0, window_delta, t1_increment):
            obs_shrinking_slice = obs[:, j:window_size]

            success, params_dict = self.fit(max_searches, obs=obs_shrinking_slice)

            if not success:
                continue

            nested_t1 = obs_shrinking_slice[0][0]
            nested_t2 = obs_shrinking_slice[0][-1]

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
            "p1": p1,
            "p2": p2,
            "windows": windows,
            "t1_index": t1_index,
            "t2_index": t2_index,
        }
