from typing import List, Dict, Tuple
from scipy.optimize import minimize
from lppls_math import LPPLSMath
import numpy as np
import random
from filter_interface import FilterInterface
import data_loader
from count_metrics import CountMetrics

class FilterShanghai(FilterInterface):
    def __init__(self, filter_file="./lppls/conf/shanghai1_filter.json"):
        self.filter_criteria = data_loader.load_config(filter_file)

    def fit(
        self, max_searches: int, obs: np.ndarray, minimizer: str = "Nelder-Mead"
    ) -> Tuple[bool, Dict[str, float]]:
        """
        Args:
            max_searches (int): The maximum number of searches to perform before giving up. The literature suggests 25.
            obs (Mx2 numpy array): the observed time-series data. Optional, if not included will use self.scaled_obs
            minimizer (str): See list of valid methods to pass to scipy.optimize.minimize:
                https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html#scipy.optimize.minimize
        Returns:
            A tuple with a boolean indicating success, and a dictionary with the values of tc, m, w, a, b, c, c1, c2, O, D
        """

        search_count = 0
        # find bubble
        while search_count < max_searches:
            t1 = obs[0, 0]
            t2 = obs[0, -1]
            t_delta = t2 - t1
            t_delta_lower = t_delta * self.filter_criteria.get("tc_delta_min")
            t_delta_upper = t_delta * self.filter_criteria.get("tc_delta_max")

            tc_bounds = (max(t1, t2 - t_delta_lower), t2 + t_delta_upper)
            m_bounds = (self.filter_criteria.get("m_min"), self.filter_criteria.get("m_max"))
            w_bounds = (self.filter_criteria.get("w_min"), self.filter_criteria.get("w_max"))
            search_bounds = [tc_bounds, m_bounds, w_bounds]

            tc = random.uniform(*tc_bounds)
            m = random.uniform(*m_bounds)
            w = random.uniform(*w_bounds)

            seed = np.array([tc, m, w])

            success, params_dict = self.estimate_params(obs, seed, minimizer, search_bounds)

            if success:
                tc, m, w, a, b, c, c1, c2 = params_dict.values()
                # O = FilterShanghai.get_oscillations(w, tc, t1, t2)
                D = FilterInterface.get_damping(m, w, b, c)
                final_dict = {
                    "tc": tc,
                    "m": m,
                    "w": w,
                    "a": a,
                    "b": b,
                    "c": c,
                    "c1": c1,
                    "c2": c2,
                    "D": D,
                }
                return True, final_dict
            else:
                search_count += 1

        CountMetrics.add_bubble_rejected_because_can_not_fit()
        return False, {}


    def estimate_params(
        self,
        observations: np.ndarray,
        seed: np.ndarray,
        minimizer: str,
        search_bounds: List[Tuple[float, float]],
    ) -> Tuple[bool, Dict[str, float]]:
        """
        Args:
            observations (np.ndarray):  the observed time-series data.
            seed (list):  time-critical, omega, and m.
            minimizer (str):  See list of valid methods to pass to scipy.optimize.minimize:
                https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html#scipy.optimize.minimize
        Returns:
            A tuple with a boolean indicating success, and a dictionary with the values of tc, m, w, a, b, c, c1, c2.
        """

        cofs = minimize(
            args=observations,
            fun=LPPLSMath.minimize_squared_residuals,
            x0=seed,
            method=minimizer,
            bounds=search_bounds,
        )

        if cofs.success:
            tc = cofs.x[0]
            m = cofs.x[1]
            w = cofs.x[2]
            obs_up_to_tc = LPPLSMath.stop_observation_at_tc(observations, tc)

            rM = LPPLSMath.matrix_equation(obs_up_to_tc, tc, m, w)
            a, b, c1, c2 = rM[:, 0].tolist()

            c = LPPLSMath.get_c(c1, c2)

            params_dict = {"tc": tc, "m": m, "w": w, "a": a, "b": b, "c": c, "c1": c1, "c2": c2}
            return True, params_dict
        else:
            return False, {}

    def check_bubble_fit(
        self, fits: Dict[str, float], observations: List[List[float]], t1_index: int, t2_index: int
    ) -> Tuple[bool, bool]:
        t1, t2, tc, m, w, a, b, c, c1, c2, D = (
            fits[key] for key in ["t1", "t2", "tc", "m", "w", "a", "b", "c", "c1", "c2", "D"]
        )

        obs_up_to_tc = LPPLSMath.stop_observation_at_tc(observations, tc)
        prices_in_range = super().is_price_in_range(
            obs_up_to_tc,
            t1_index,
            t2_index,
            self.filter_criteria.get("relative_error_max"),
            tc,
            m,
            w,
            a,
            b,
            c1,
            c2,
        )

        t_delta = t2 - t1
        t_delta_lower = t_delta * self.filter_criteria.get("tc_delta_min")
        t_delta_upper = t_delta * self.filter_criteria.get("tc_delta_max")

        assert max(t1, t2 - t_delta_lower) <= tc <= t2 + t_delta_upper
        assert self.filter_criteria.get("m_min") <= m <= self.filter_criteria.get("m_max")
        assert self.filter_criteria.get("w_min") <= w <= self.filter_criteria.get("w_max")

        # if b != 0 and c != 0:
        #     O = O
        # else:
        #     O = np.inf
        # O_in_range = O >= self.filter_criteria.get("O_min")

        D_in_range = D >= self.filter_criteria.get("D_min")

        if D_in_range and prices_in_range:
            is_qualified = True
            CountMetrics.add_bubble_accepted()
        else:
            CountMetrics.add_rejected_bubble(D_in_range, prices_in_range)
            is_qualified = False

        # if B is negative, the predicted price will increase in value as t tends to tc (because 0 < m < 1)
        is_positive_bubble = b < 0

        return is_qualified, is_positive_bubble

    @staticmethod
    def get_oscillations(w: float, tc: float, t1: float, t2: float) -> float:
        assert t1 < tc, "we can only compute oscillations above the starting time"
        # In the Shanghai paper, we divide by (t2 - t1), but that must be incorrect
        return (w / 2.0) * np.log((tc - t1) / (tc - t2))
