from typing import List, Dict, Tuple
from scipy.optimize import minimize
from scipy.signal import lombscargle
from lppls_math import LPPLSMath
import numpy as np
import random
from filter_interface import FilterInterface
import data_loader
from statsmodels.tsa.ar_model import AutoReg
from lppls_defaults import SIGNIFICANCE_LEVEL
from count_metrics import CountMetrics
from lppls_dataclasses import ObservationSeries, OptimizedParams, OptimizedInterval


# This filter is descipted in paper 1:
# Real-time Prediction of Bitcoin Bubble Crashes (2019)
# Authors: Min Shu, Wei Zhu
#
# And also in paper 2:
# Birth or burst of financial bubbles: which one is easier to diagnose (2015)
# Authors: Guilherme Demos, Qunzhi Zhang, Didier Sornette
# https://ssrn.com/abstract=2699164
class FilterBitcoin2019B(FilterInterface):
    def __init__(self, filter_file="./lppls/conf/bitcoin2019_filterB.json"):
        self.filter_criteria = data_loader.load_config(filter_file)

    def fit(
        self, max_searches: int, observations: ObservationSeries, minimizer: str = "Nelder-Mead"
    ) -> OptimizedParams:
        """
        Args:
            max_searches (int): The maximum number of searches to perform before giving up. The literature suggests 25.
            obs (Mx2 numpy array): the observed time-series data. Optional, if not included will use self.scaled_obs
            minimizer (str): See list of valid methods to pass to scipy.optimize.minimize:
                https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html#scipy.optimize.minimize
        Returns:
            A tuple with a boolean indicating success, and a dictionary with the values of tc, m, w, a, b, c, c1, c2, O, D
        """

        t1 = observations[0].date_ordinal
        t2 = observations[-1].date_ordinal
        tc_bounds = (t2 + 1, t2 + (t2 - t1) * self.filter_criteria.get("tc_extra_space"))
        m_bounds = (self.filter_criteria.get("m_min"), self.filter_criteria.get("m_max"))
        w_bounds = (self.filter_criteria.get("w_min"), self.filter_criteria.get("w_max"))
        search_bounds = [tc_bounds, m_bounds, w_bounds]

        search_count = 0
        # find bubble
        while search_count < max_searches:
            tc = random.uniform(*tc_bounds)
            m = random.uniform(*m_bounds)
            w = random.uniform(*w_bounds)

            seed = np.array([tc, m, w])

            fit = self.estimate_params(observations, seed, minimizer, search_bounds)

            if fit:
                return fit

            search_count += 1

        CountMetrics.add_bubble_rejected_because_can_not_fit()
        return None


    def estimate_params(
        self,
        observations: ObservationSeries,
        seed: np.ndarray,
        minimizer: str,
        search_bounds: List[Tuple[float, float]],
    ) -> OptimizedParams:

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

            rM = LPPLSMath.matrix_equation(observations, tc, m, w)
            a, b, c1, c2 = rM[:, 0].tolist()


            return OptimizedParams(tc, m, w, a, b, c1, c2)
        else:
            return None


    def check_bubble_fit(self, oi: OptimizedInterval, observations: ObservationSeries, t1_index: int, t2_index: int) -> Tuple[bool, bool]:
        op = oi.optimized_params
        tc, m, w, a, b = op.tc, op.m, op.w, op.a, op.b
        t1, t2 = oi.t1, oi.t2
        c = LPPLSMath.get_c(op.c1, op.c2)

        observations = observations.filter_before_tc(tc)
        prices_in_range = super().is_price_in_range(
            observations,
            t1_index,
            t2_index,
            self.filter_criteria.get("relative_error_max"),
            op
        )

        tc_extra_space = self.filter_criteria.get("tc_extra_space")
        assert t2 + 1 <= tc <= t2 + ((t2 - t1) * tc_extra_space)
        assert self.filter_criteria.get("m_min") <= m <= self.filter_criteria.get("m_max")
        assert self.filter_criteria.get("w_min") <= w <= self.filter_criteria.get("w_max")

        oscillations_divisor = self.filter_criteria.get("oscillations_divisor")
        O_min = self.filter_criteria.get("O_min")
        min_c_b_ratio = self.filter_criteria.get("min_c_b_ratio")
        O_in_range = FilterInterface.are_oscillations_in_range(
            w, oscillations_divisor, tc, t1, t2, O_min, b, c, min_c_b_ratio
        )

        D = FilterInterface.get_damping(m, w, b, c)
        D_in_range = D >= self.filter_criteria.get("D_min")

        passing_lomb_test = FilterBitcoin2019B.is_passing_lomb_test(observations, tc, m, a, b)
        passing_ar1_test = self.is_ar1_process(observations, tc, m, a, b)

        conditions = {
            "O": O_in_range,
            "D": D_in_range,
            "price": prices_in_range,
            "lomb_test": passing_lomb_test,
            "ar1_test": passing_ar1_test,
        }

        CountMetrics.add_bubble(conditions, t2_index)

        is_qualified = (
            O_in_range and D_in_range and prices_in_range and passing_lomb_test and passing_ar1_test
        )

        # if B is negative, the predicted price will increase in value as t tends to tc (because 0 < m < 1)
        is_positive_bubble = b < 0

        return is_qualified, is_positive_bubble

    @staticmethod
    def is_ar1_process(
        observations: ObservationSeries, tc: float, m: float, a: float, b: float
    ) -> bool:
        # Compute the residuals between predicted and actual log prices
        residuals = []
        for observation in observations:
            time, log_price = observation.date_ordinal, np.log(observation.price)
            predicted_log_price = a + b * (tc - time) ** m
            # not taking the log of the price because the price is already in log
            residuals.append(predicted_log_price - log_price)

        # OptimizedParams an AR(1) model to the residuals
        ar1_model = AutoReg(residuals, lags=1).fit()

        # Get the p-value for the AR(1) coefficient
        p_value = ar1_model.pvalues[1]  # p-value for the AR(1) coefficient

        # Check if the p-value is less than or equal to your significance level
        return p_value <= SIGNIFICANCE_LEVEL

    @staticmethod
    def is_passing_lomb_test(
        observations: ObservationSeries, tc: float, m: float, a: float, b: float
    ) -> bool:
        # Compute the detrended residuals
        residuals = []
        for observation in observations:
            time, log_price = observation.date_ordinal, np.log(observation.price)
            # not taking the log of the price because the price is already in log
            residuals.append((tc - time) ** (-m) * (log_price - a - b * (tc - time) ** m))

        # Compute the Lomb-Scargle periodogram
        f = np.linspace(0.01, 1, len(observations))  # Frequency range, adjust as needed
        pgram = lombscargle(observations.get_log_prices(), residuals, f)

        # Find the peak power
        peak_power = np.max(pgram)

        # Compute the p-value for the peak power
        p_lomb = 1 - np.exp(-peak_power)

        # Check if the p-value is less than or equal to your significance level
        return p_lomb <= SIGNIFICANCE_LEVEL
