from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Tuple, List
from lppls_math import LPPLSMath

class FilterInterface(ABC):

    @abstractmethod
    def fit(self, max_searches: int, obs: np.ndarray, minimizer: str) -> Tuple[bool, Dict[str, float]]:
        pass

    @abstractmethod
    def check_bubble_fit(self, fits: Dict[str, float], observations: List[List[float]], t1_index: int, t2_index: int) -> Tuple[bool, bool]:
        pass


    def is_price_in_range(self, observations: List[List[float]], t1_index: int, t2_index: int, relative_error_max: float, tc: float, m: float, w: float, a: float, b: float, c1: float, c2: float) -> bool:
        for i in range(t1_index, min(len(observations[0]), t2_index)):
            t, p = observations[0][i], observations[1][i]
            predicted_price = np.exp(LPPLSMath.lppls(t, tc, m, w, a, b, c1, c2))
            actual_price = np.exp(p)

            prediction_error = abs(actual_price - predicted_price)/actual_price

            if prediction_error > relative_error_max:
                return False

        return True
