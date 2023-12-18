from typing import List, Tuple
from scipy.optimize import minimize
from scipy.signal import lombscargle
from lppls_math import LPPLSMath
import numpy as np
import random
from filter_interface import FilterInterface
import data_loader
from statsmodels.tsa.ar_model import AutoReg
from lppls_defaults import (
    SIGNIFICANCE_LEVEL,
    ADF_SIGNIFICANCE_LEVEL,
    MAX_SEARCHES,
    TRIES_TO_GET_MINIMUM,
)
from lppls_dataclasses import (
    ObservationSeries,
    OptimizedParams,
    OptimizedInterval,
    RejectionReason,
    BubbleType,
    BubbleFit,
)
from statsmodels.tsa.stattools import adfuller


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
        self, observations: ObservationSeries, minimizer: str = "Nelder-Mead"
    ) -> OptimizedParams | None:
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

        tries = 0
        min_fit, min_error = None, np.inf
        # find bubble
        for _ in range(0, MAX_SEARCHES):
            tc = random.uniform(*tc_bounds)
            m = random.uniform(*m_bounds)
            w = random.uniform(*w_bounds)

            seed = np.array([tc, m, w])

            fit = self.estimate_params(observations, seed, minimizer, search_bounds)
            if not fit:
                continue

            tries += 1
            current_error = self.compute_price_error(observations, fit)
            if current_error < min_error:
                min_fit = fit
                min_error = current_error

            if tries == TRIES_TO_GET_MINIMUM:
                assert min_fit != np.inf
                return min_fit

        return min_fit

    def compute_price_error(
        self, observations: ObservationSeries, optimized_params: OptimizedParams
    ) -> float:
        predicted_prices = LPPLSMath.get_log_price_predictions(observations, optimized_params)
        actual_prices = observations.get_log_prices()
        return sum(
            [(actual_prices[i] - predicted_prices[i]) ** 2 for i in range(len(actual_prices))]
        )

    def estimate_params(
        self,
        observations: ObservationSeries,
        seed: np.ndarray,
        minimizer: str,
        search_bounds: List[Tuple[float, float]],
    ) -> OptimizedParams | None:
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

    def check_bubble_fit(
        self,
        oi: OptimizedInterval,
        observations: ObservationSeries,
        should_optimize: bool,
    ) -> BubbleFit:
        op = oi.optimized_params
        tc, m, w, a, b = op.tc, op.m, op.w, op.a, op.b
        t1, t2 = oi.t1, oi.t2
        c = LPPLSMath.get_c(op.c1, op.c2)

        tc_extra_space = self.filter_criteria.get("tc_extra_space")
        assert t2 + 1 <= tc <= t2 + ((t2 - t1) * tc_extra_space)
        assert self.filter_criteria.get("m_min") <= m <= self.filter_criteria.get("m_max")
        assert self.filter_criteria.get("w_min") <= w <= self.filter_criteria.get("w_max")

        # if B is negative, the predicted price will increase in value as t tends to tc (because 0 < m < 1)
        bubble_type = BubbleType.POSITIVE if b < 0 else BubbleType.NEGATIVE

        D = FilterInterface.get_damping(m, w, b, c)
        D_in_range = D >= self.filter_criteria.get("D_min")
        if should_optimize and not D_in_range:
            return BubbleFit([RejectionReason.ANY_REASON], type=bubble_type)

        oscillations_divisor = self.filter_criteria.get("oscillations_divisor")
        O_min = self.filter_criteria.get("O_min")
        min_c_b_ratio = self.filter_criteria.get("min_c_b_ratio")
        O_in_range = FilterInterface.are_oscillations_in_range(
            w, oscillations_divisor, tc, t1, t2, O_min, b, c, min_c_b_ratio
        )
        if should_optimize and not O_in_range:
            return BubbleFit([RejectionReason.ANY_REASON], type=bubble_type)

        obs_within_t1_t2 = observations.filter_before_tc(tc)[oi.t1_index : oi.t2_index]
        prices_in_range = super().is_price_in_range(
            obs_within_t1_t2, self.filter_criteria.get("relative_error_max"), op
        )
        if should_optimize and not prices_in_range:
            return BubbleFit([RejectionReason.ANY_REASON], type=bubble_type)

        passing_lomb_test = self.is_passing_lomb_test(obs_within_t1_t2, tc, m, a, b)
        if should_optimize and not passing_lomb_test:
            return BubbleFit([RejectionReason.ANY_REASON], type=bubble_type)

        passing_ar1_test = self.is_ar1_process(obs_within_t1_t2, op)
        if should_optimize and not passing_ar1_test:
            return BubbleFit([RejectionReason.ANY_REASON], type=bubble_type)

        rejection_reasons = []
        if not O_in_range:
            rejection_reasons.append(RejectionReason.OSCILLATIONS)
        if not D_in_range:
            rejection_reasons.append(RejectionReason.DAMPING)
        if not prices_in_range:
            rejection_reasons.append(RejectionReason.PRICE_DELTA)
        if not passing_lomb_test:
            rejection_reasons.append(RejectionReason.LOMB_TEST)
        if not passing_ar1_test:
            rejection_reasons.append(RejectionReason.AR1_TEST)

        return BubbleFit(rejection_reasons, type=bubble_type)

    def is_ar1_process(
        self, observations: ObservationSeries, optimized_params: OptimizedParams
    ) -> bool:
        # Compute the residuals between predicted and actual log prices
        residuals = []
        for observation in observations:
            date_ordinal, log_price = observation.date_ordinal, np.log(observation.price)
            predicted_log_price = LPPLSMath.predict_log_price(date_ordinal, optimized_params)
            # not taking the log of the price because the price is already in log
            residuals.append(predicted_log_price - log_price)

        # OptimizedParams an AR(1) model to the residuals
        ar1_model = AutoReg(residuals, lags=1).fit()

        # Get the p-value for the AR(1) coefficient
        p_value_ar1 = ar1_model.pvalues[1]  # p-value for the AR(1) coefficient

        # Perform Dickey-Fuller unit-root test
        df_test = adfuller(residuals)
        p_value_df = df_test[1]  # p-value from the Dickey-Fuller test

        # Check if the p-value is less than or equal to your significance level
        return bool(p_value_ar1 <= SIGNIFICANCE_LEVEL and p_value_df <= ADF_SIGNIFICANCE_LEVEL)

    # Here, I need to remove the trend in prices and keep only the osciallations
    # See 'Why Stock Markets Crash' by Sornette, page 263-264
    # For formula, see:
    # Page 10, Real-time Prediction of Bitcoin Bubble Crashes (2019)
    # Authors: Min Shu, Wei Zhu
    def is_passing_lomb_test(
        self, observations: ObservationSeries, tc: float, m: float, a: float, b: float
    ) -> bool:
        # Compute the detrended residuals
        residuals = []
        for observation in observations:
            time, log_price = observation.date_ordinal, np.log(observation.price)
            # not taking the log of the price because the price is already in log

            time_component = (tc - time) ** m
            non_osciallating_price = a + b * time_component
            residual = (log_price - non_osciallating_price) / time_component
            residuals.append(residual)

        # Compute the Lomb-Scargle periodogram
        f = np.linspace(0.01, 1, len(observations))  # Frequency range, adjust as needed
        pgram = lombscargle(observations.get_date_ordinals(), residuals, f)

        # Find the peak power
        peak_power = np.max(pgram)

        # Compute the p-value for the peak power
        p_lomb = 1 - np.exp(-peak_power)

        # Check if the p-value is less than or equal to your significance level
        return bool(p_lomb <= SIGNIFICANCE_LEVEL)
