from typing import List, Dict, Any, Union, Tuple
import numpy as np
from scipy.optimize import minimize
import random
from lppls_math import LPPLSMath
from datetime import datetime as date
from pandas._libs.tslibs.np_datetime import OutOfBoundsDatetime
from tqdm import tqdm
import xarray as xr
import pandas as pd
from matplotlib import pyplot as plt
from multiprocessing import Pool
from lppls_defaults import LARGEST_WINDOW_SIZE, SMALLEST_WINDOW_SIZE, T1_STEP, T2_STEP, MAX_SEARCHES
import traceback

class DataFit:

    def __init__(self, observations, filter):
        self.observations = observations
        self.filter = filter


    def plot_fit(self, coef):
        """
        Args:
            observations (Mx2 numpy array): the observed data
        Returns:
            nothing, should plot the fit
        """
        print('coef:', coef)
        tc, m, w, a, b, c, c1, c2, O, D = coef.values()

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


    def fit(self, max_searches: int, obs: np.ndarray, minimizer: str = 'Nelder-Mead') -> dict:
        """
        Args:
            max_searches (int): The maximum number of searches to perform before giving up. The literature suggests 25.
            obs (Mx2 numpy array): the observed time-series data. Optional, if not included will use self.scaled_obs
            minimizer (str): See list of valid methods to pass to scipy.optimize.minimize:
                https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html#scipy.optimize.minimize
        Returns:
            tc, m, w, a, b, c, c1, c2, O, D
        """

        search_count = 0
        # find bubble
        while search_count < max_searches:
            t1 = obs[0, 0]
            t2 = obs[0, -1]
            t_delta = t2 - t1
            t_delta_lower = t_delta * self.filter.get("tc_delta_min")
            t_delta_upper = t_delta * self.filter.get("tc_delta_max")

            tc_bounds = (max(t1, t2 - t_delta_lower), t2 + t_delta_upper)
            m_bounds = (self.filter.get("m_min"), self.filter.get("m_max"))
            w_bounds = (self.filter.get("w_min"), self.filter.get("w_max"))
            search_bounds = [tc_bounds, m_bounds, w_bounds]

            tc = random.uniform(*tc_bounds)
            m = random.uniform(*m_bounds)
            w = random.uniform(*w_bounds)

            seed = np.array([tc, m, w])

            try:
                tc, m, w, a, b, c, c1, c2 = self.estimate_params(obs, seed, minimizer, search_bounds)
                O = LPPLSMath.get_oscillations(w, tc, t1, t2)
                D = LPPLSMath.get_damping(m, w, b, c)
                return {'tc': tc, 'm': m, 'w': w, 'a': a, 'b': b, 'c': c, 'c1': c1, 'c2': c2, 'O': O, 'D': D}
            except Exception as e:
                search_count += 1
                print('Exception in fitting: ' + ''.join(traceback.format_exception(type(e), e, e.__traceback__)))


        print('from fitting, returning all parameters 0')
        return {'tc': 0, 'm': 0, 'w': 0, 'a': 0, 'b': 0, 'c': 0, 'c1': 0, 'c2': 0, 'O': 0, 'D': 0}


    def estimate_params(self, observations: np.ndarray, seed: np.ndarray, minimizer: str, search_bounds: List[Tuple[float, float]]) -> Union[Tuple[float, float, float, float, float, float, float, float], UnboundLocalError]:
        """
        Args:
            observations (np.ndarray):  the observed time-series data.
            seed (list):  time-critical, omega, and m.
            minimizer (str):  See list of valid methods to pass to scipy.optimize.minimize:
                https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html#scipy.optimize.minimize
        Returns:
            tc, m, w, a, b, c, c1, c2
        """

        cofs = minimize(
            args=observations,
            fun=LPPLSMath.sum_of_squared_residuals,
            x0=seed,
            method=minimizer,
            bounds=search_bounds
        )

        if cofs.success:
            tc = cofs.x[0]
            m = cofs.x[1]
            w = cofs.x[2]
            obs_up_to_tc = LPPLSMath.stop_observation_at_tc(observations, tc)

            rM = LPPLSMath.matrix_equation(obs_up_to_tc, tc, m, w)
            a, b, c1, c2 = rM[:, 0].tolist()

            c = LPPLSMath.get_c(c1, c2)

            return tc, m, w, a, b, c, c1, c2
        else:
            raise UnboundLocalError


    def mp_compute_t1_fits(self, workers, window_size=LARGEST_WINDOW_SIZE, smallest_window_size=SMALLEST_WINDOW_SIZE, outer_increment=T1_STEP, inner_increment=T2_STEP, max_searches=MAX_SEARCHES):
        obs_copy = self.observations
        obs_copy_len = len(obs_copy[0]) - window_size
        func = self.compute_t2_fits

        func_arg_map = []
        for i in range(0, obs_copy_len + 1, outer_increment):
            args = (
                obs_copy[:, i:window_size + i],
                window_size,
                i,
                smallest_window_size,
                inner_increment,
                max_searches,
            )
            func_arg_map.append(args)


        lppls_fits = []
        with Pool(processes=workers) as pool:
            lppls_fits = list(tqdm(pool.imap(func, func_arg_map), total=len(func_arg_map)))

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

            tc, m, w, a, b, c, c1, c2, O, D = self.fit(max_searches, obs=obs_shrinking_slice).values()

            nested_t1 = obs_shrinking_slice[0][0]
            nested_t2 = obs_shrinking_slice[0][-1]


            windows.append({
                'tc_d': self.ordinal_to_date(tc),
                'tc': tc,
                'm': m,
                'w': w,
                'a': a,
                'b': b,
                'c': c,
                'c1': c1,
                'c2': c2,
                't1_d': self.ordinal_to_date(nested_t1),
                't2_d': self.ordinal_to_date(nested_t2),
                't1': nested_t1,
                't2': nested_t2,
                'O': O,
                'D': D,
            })

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


    def compute_t1_fits(self, window_size=LARGEST_WINDOW_SIZE, smallest_window_size=LARGEST_WINDOW_SIZE, outer_increment=T1_STEP, inner_increment=T2_STEP,
                            max_searches=MAX_SEARCHES):
        obs_copy = self.observations
        obs_copy_len = len(obs_copy[0]) - window_size
        window_delta = window_size - smallest_window_size
        known_price_span = []
        i_idx = 0
        for i in range(0, obs_copy_len + 1, outer_increment):
            j_idx = 0
            obs = obs_copy[:, i:window_size + i]
            t1 = obs[0][0]
            t2 = obs[0][-1]
            known_price_span.append([])
            i_idx += 1
            for j in range(0, window_delta, inner_increment):
                obs_shrinking_slice = obs[:, j:window_size]
                tc, m, w, a, b, c, c1, c2, O, D = self.fit(max_searches, obs=obs_shrinking_slice)
                known_price_span[i_idx-1].append([])
                j_idx += 1
                for k in [t2, t1, a, b, c, m, 0, tc]:
                    known_price_span[i_idx-1][j_idx-1].append(k)
        return xr.DataArray(
            data=known_price_span,
            dims=('t2', 'windowsizes', 'params'),
            coords=dict(
                        t2=obs_copy[0][(window_size-1):],
                        windowsizes=range(smallest_window_size, window_size, inner_increment),
                        params=['t2', 't1', 'a', 'b', 'c', 'm', '0', 'tc'],
                        )
        )