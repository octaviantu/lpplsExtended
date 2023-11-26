from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Tuple
from lppls_math import LPPLSMath
from lppls_dataclasses import ObservationSeries, OptimizedParams, OptimizedInterval


class FilterInterface(ABC):
    @abstractmethod
    def fit(
        self, max_searches: int, obsservations: ObservationSeries, minimizer: str
    ) -> OptimizedParams | None:
        pass

    @abstractmethod
    def check_bubble_fit(
        self, oi: OptimizedInterval, observations: ObservationSeries, t1_index: int, t2_index: int
    ) -> Tuple[bool, bool]:
        pass

    def is_price_in_range(
        self,
        observations: ObservationSeries,
        t1_index: int,
        t2_index: int,
        relative_error_max: float,
        optimized_params: OptimizedParams,
    ) -> bool:
        for observation in observations[t1_index:t2_index]:
            actual_log_price, date_ordinal = np.log(observation.price), observation.date_ordinal
            predicted_log_price = LPPLSMath.predict_log_price(date_ordinal, optimized_params)

            # In some papers such as the one underneath they are using the price, not its log.
            # However, in practice that will exclude all large enough windows because there is bound to be a
            # price difference larger than the prediction error, especially since we are not optimising for that
            # in the minimizer
            #
            # Real-time Prediction of Bitcoin Bubble Crashes
            # Authors: Min Shu, Wei Zhu
            prediction_error = abs(actual_log_price - predicted_log_price) / actual_log_price

            if prediction_error > relative_error_max:
                return False

        return True

    @staticmethod
    def get_damping(m: float, w: float, b: float, c: float) -> float:
        # this is the value in the Shanghai paper, but I recomputed
        # return (m * np.abs(b)) / (w * np.abs(c))
        return (m * np.abs(b)) / (np.sqrt(pow(w, 2) + pow(m, 2)) * np.abs(c))

    @staticmethod
    def are_oscillations_in_range(
        w: float,
        oscillations_divisor: float,
        tc: float,
        t1: float,
        t2: float,
        O_min: float,
        b: float,
        c: float,
        min_c_b_ratio: float,
    ) -> bool:
        #  From Swiss Finance - Dissection of Bitcoin's Multiscale Bubble History (2018)
        #  G. C. Gerlach, Guilherme Demos, Didier Sornette
        if np.abs(c / b) < min_c_b_ratio:
            return True

        assert t1 < tc, "we can only compute oscillations above the starting time"
        # here the divisior is different:
        # - in paper 1 it's 2
        # - in paper 2 it's pi
        O = (w / oscillations_divisor) * np.log((tc - t1) / (tc - t2))
        return O >= O_min
