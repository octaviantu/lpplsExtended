from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Tuple, List

class FilterInterface(ABC):

    @abstractmethod
    def fit(self, max_searches: int, obs: np.ndarray, minimizer: str) -> Tuple[bool, Dict[str, float]]:
        pass

    @abstractmethod
    def check_bubble_fit(self, fits: Dict[str, float], observations: List[List[float]], t1_index: int, t2_index: int) -> Tuple[bool, bool]:
        pass
