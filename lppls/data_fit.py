from typing import List, Dict, Any, Union, Tuple
import numpy as np
import random
from lppls_math import LPPLSMath
from datetime import datetime as date
from pandas._libs.tslibs.np_datetime import OutOfBoundsDatetime
from tqdm import tqdm
import pandas as pd
from matplotlib import pyplot as plt
from multiprocessing import Pool
from lppls_defaults import LARGEST_WINDOW_SIZE, SMALLEST_WINDOW_SIZE, T1_STEP, T2_STEP, MAX_SEARCHES
from filter_interface import FilterInterface

class DataFit:

    def __init__(self, observations, filter: FilterInterface):
        self.observations = observations
        self.filter = filter


    def plot_fit(self, tc: float, m: float, w: float, a: float, b: float, c1: float, c2: float)-> None:

        obs_up_to_tc = LPPLSMath.stop_observation_at_tc(self.observations, tc)
        time_ord = [pd.Timestamp.fromordinal(int(d)) for d in obs_up_to_tc[0]]

        [price_prediction, actual_prices] = LPPLSMath.get_price_predictions(obs_up_to_tc, tc, m, w, a, b, c1, c2)

        _, (ax1) = plt.subplots(nrows=1, ncols=1, sharex=True, figsize=(14, 8))

        ax1.plot(time_ord, actual_prices, label='price', color='black', linewidth=0.75)
        ax1.plot(time_ord, price_prediction, label='lppls fit', color='blue', alpha=0.5)

        # set grids
        ax1.grid(which='major', axis='both', linestyle='--')
        # set labels
        ax1.set_ylabel('ln(p)')
        ax1.legend(loc=2)

        plt.xticks(rotation=45)


    def fit(self, max_searches: int, obs: np.ndarray, minimizer: str = 'Nelder-Mead') -> Tuple[bool, Dict[str, float]]:
        return self.filter.fit(max_searches, obs, minimizer)


    def mp_compute_t1_fits(self, workers, window_size=LARGEST_WINDOW_SIZE, smallest_window_size=SMALLEST_WINDOW_SIZE, outer_increment=T1_STEP, inner_increment=T2_STEP, max_searches=MAX_SEARCHES):
        obs_copy = self.observations
        obs_copy_len = len(obs_copy[0]) - window_size

        t2_fits_args = []
        for i in range(0, obs_copy_len + 1, outer_increment):
            args = (
                obs_copy[:, i:window_size + i],
                window_size,
                i,
                smallest_window_size,
                inner_increment,
                max_searches,
            )
            t2_fits_args.append(args)


        lppls_fits = []
        with Pool(processes=workers) as pool:
            lppls_fits = list(tqdm(pool.imap(self.compute_t2_fits, t2_fits_args), total=len(t2_fits_args)))

        return lppls_fits


    def compute_t2_fits(self, args):

        obs, window_size, t1_index, smallest_window_size, inner_increment, max_searches = args

        window_delta = window_size - smallest_window_size

        windows = []

        t1 = obs[0][0]
        t2 = obs[0][-1]
        p1 = obs[1][0]
        p2 = obs[1][-1]

        # have to store two indexes because trading days don't map to calendar days
        t2_index = t1_index + len(obs[0]) - 1

        # run n fits on the observation slice.
        for j in range(0, window_delta, inner_increment):
            obs_shrinking_slice = obs[:, j:window_size]

            success, params_dict = self.fit(max_searches, obs=obs_shrinking_slice)

            if not success:
                continue

            nested_t1 = obs_shrinking_slice[0][0]
            nested_t2 = obs_shrinking_slice[0][-1]

            # Update params_dict with new key-value pairs
            params_dict.update({
                't1_d': self.ordinal_to_date(nested_t1),
                't2_d': self.ordinal_to_date(nested_t2),
                't1': nested_t1,
                't2': nested_t2,
            })

            # Append updated params_dict to windows
            windows.append(params_dict)

        return {'t1': t1, 't2': t2, 'p1': p1, 'p2': p2, 'windows': windows, 't1_index': t1_index, 't2_index': t2_index}


    def ordinal_to_date(self, ordinal):
        # Since pandas represents timestamps in nanosecond resolution,
        # the time span that can be represented using a 64-bit integer
        # is limited to approximately 584 years
        try:
            return date.fromordinal(int(ordinal)).strftime('%Y-%m-%d')
        except (ValueError, OutOfBoundsDatetime):
            return str(pd.NaT)


    # This is old code
    # TODO(octaviant) - figure out what this does 
    def _get_tc_bounds(self, obs, lower_bound_pct, upper_bound_pct):
        """
        Args:
            obs (Mx2 numpy array): the observed data
            lower_bound_pct (float): percent of (t_2 - t_1) to use as the LOWER bound initial value for the optimization
            upper_bound_pct (float): percent of (t_2 - t_1) to use as the UPPER bound initial value for the optimization
        Returns:
            tc_init_min, tc_init_max
        """
        t_first = obs[0][0]
        t_last = obs[0][-1]
        t_delta = t_last - t_first
        pct_delta_min = t_delta * lower_bound_pct
        pct_delta_max = t_delta * upper_bound_pct
        tc_init_min = t_last - pct_delta_min
        tc_init_max = t_last + pct_delta_max
        return tc_init_min, tc_init_max


    # def compute_t1_fits(self, window_size=LARGEST_WINDOW_SIZE, smallest_window_size=LARGEST_WINDOW_SIZE, outer_increment=T1_STEP, inner_increment=T2_STEP,
    #                         max_searches=MAX_SEARCHES):
    #     obs_copy = self.observations
    #     obs_copy_len = len(obs_copy[0]) - window_size
    #     window_delta = window_size - smallest_window_size
    #     known_price_span = []
    #     i_idx = 0
    #     for i in range(0, obs_copy_len + 1, outer_increment):
    #         j_idx = 0
    #         obs = obs_copy[:, i:window_size + i]
    #         t1 = obs[0][0]
    #         t2 = obs[0][-1]
    #         known_price_span.append([])
    #         i_idx += 1
    #         for j in range(0, window_delta, inner_increment):
    #             obs_shrinking_slice = obs[:, j:window_size]
    #             tc, m, w, a, b, c, c1, c2, O, D = self.fit(max_searches, obs=obs_shrinking_slice)
    #             known_price_span[i_idx-1].append([])
    #             j_idx += 1
    #             for k in [t2, t1, a, b, c, m, 0, tc]:
    #                 known_price_span[i_idx-1][j_idx-1].append(k)
    #     return xr.DataArray(
    #         data=known_price_span,
    #         dims=('t2', 'windowsizes', 'params'),
    #         coords=dict(
    #                     t2=obs_copy[0][(window_size-1):],
    #                     windowsizes=range(smallest_window_size, window_size, inner_increment),
    #                     params=['t2', 't1', 'a', 'b', 'c', 'm', '0', 'tc'],
    #                     )
    #     )