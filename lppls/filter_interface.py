from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Tuple, List
from lppls_math import LPPLSMath


class FilterInterface(ABC):
    @abstractmethod
    def fit(
        self, max_searches: int, obs: np.ndarray, minimizer: str
    ) -> Tuple[bool, Dict[str, float]]:
        pass

    @abstractmethod
    def check_bubble_fit(
        self, fits: Dict[str, float], observations: List[List[float]], t1_index: int, t2_index: int
    ) -> Tuple[bool, bool]:
        pass

    def is_price_in_range(
        self,
        observations: List[List[float]],
        t1_index: int,
        t2_index: int,
        relative_error_max: float,
        tc: float,
        m: float,
        w: float,
        a: float,
        b: float,
        c1: float,
        c2: float,
    ) -> bool:
        for i in range(t1_index, min(len(observations[0]), t2_index)):
            t, p = observations[0][i], observations[1][i]
            predicted_price = np.exp(LPPLSMath.lppls(t, tc, m, w, a, b, c1, c2))
            actual_price = np.exp(p)

            prediction_error = abs(actual_price - predicted_price) / actual_price

            if prediction_error > relative_error_max:
                return False

        return True
    

    @staticmethod
    def get_damping(m: float, w: float, b: float, c: float) -> float:
        # this is the value in the Shanghai paper, but I recomputed
        # return (m * np.abs(b)) / (w * np.abs(c))
        return (m * np.abs(b)) / (np.sqrt(pow(w, 2) + pow(m, 2)) * np.abs(c))

    @staticmethod
    def are_oscillations_in_range(w: float, oscillations_divisor: float, tc: float, t1: float, t2: float,
                                  O_min: float, b: float, c: float, min_c_b_ratio: float) -> bool:
        #  From Swiss Finance - Dissection of Bitcoin's Multiscale Bubble History (2018)
        #  G. C. Gerlach, Guilherme Demos, Didier Sornette
        if np.abs(c/b) < min_c_b_ratio:
            return True

        assert t1 < tc, "we can only compute oscillations above the starting time"
        # here the divisior is different:
        # - in paper 1 it's 2
        # - in paper 2 it's pi
        O = (w / oscillations_divisor) * np.log((tc - t1) / (tc - t2))
        return O >= O_min
