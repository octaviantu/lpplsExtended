from enum import Enum
from dataclasses import dataclass
from typing import List
import numpy as np
from date_utils import ordinal_to_date
import sys


class BubbleType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


@dataclass
class BubbleStart:
    date_ordinal: int
    type: BubbleType


@dataclass
class Peak:
    type: BubbleType
    date_ordinal: int
    score: float


@dataclass
class Observation:
    price: float
    date_ordinal: int


@dataclass
class ObservationSeries:
    observations: List[Observation]

    def __len__(self):
        return len(self.observations)

    def __getitem__(self, key):
        if isinstance(key, slice):
            # Handle slice objects
            return ObservationSeries(self.observations[key])
        elif isinstance(key, int):
            # Handle integer index
            return self.observations[key]
        else:
            raise TypeError("Invalid argument type.")

    def __iter__(self):
        return iter(self.observations)

    def get_prices(self):
        return [o.price for o in self.observations]

    def get_log_returns(self):
        # We add a dummy first element to maintain the same index.
        log_returns = [0.0]
        for i in range(1, len(self.observations)):
            log_returns.append(
                np.log(self.observations[i].price) - np.log(self.observations[i - 1].price)
            )
        return log_returns

    def get_log_prices(self):
        return np.log(self.get_prices())

    def get_date_at_ordinal(self, date_ordinal: int):
        return self.observations[date_ordinal].date_ordinal

    def get_date_ordinals(self):
        return [o.date_ordinal for o in self.observations]

    def filter_before_tc(self, tc: float):
        first_larger_index = int(np.searchsorted(self.get_date_ordinals(), tc, side="left"))
        return ObservationSeries(self.observations[:first_larger_index])

    def filter_between_date_ordinals(
        self, start_date_ordinal: int = 0, end_date_ordinal: int = sys.maxsize
    ):
        start_index = int(
            np.searchsorted(self.get_date_ordinals(), start_date_ordinal, side="left")
        )
        end_index = int(np.searchsorted(self.get_date_ordinals(), end_date_ordinal, side="left"))
        return ObservationSeries(self.observations[start_index:end_index])

    def get_formatted_dates(self):
        return [ordinal_to_date(o.date_ordinal) for o in self.observations]

    def get_between_indexes(self, start_index: int, end_index: int):
        return ObservationSeries(self.observations[start_index:end_index])


@dataclass
class OptimizedParams:
    tc: float
    m: float
    w: float
    a: float
    b: float
    c1: float
    c2: float


@dataclass
class OptimizedInterval:
    t1: int
    t2: int
    optimized_params: OptimizedParams
    is_qualified: bool = False


# TODO(octaviant) - check if we really need t1_index, t2_index
@dataclass
class IntervalFits:
    optimized_intervals: List[OptimizedInterval]
    t1: int
    t2: int
    p2: float
    t1_index: int
    t2_index: int


@dataclass
class BubbleScore:
    t2: int
    log_price: float
    pos_conf: float
    neg_conf: float
    optimized_intervals: List[OptimizedInterval]
