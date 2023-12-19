import numpy as np
from lppls.bubble_scores import BubbleScores
from lppls.data_fit import DataFit
from lppls.filter_bitcoin2019B import FilterBitcoin2019B
from lppls.filter_interface import FilterInterface
from lppls.lppls_math import LPPLSMath
from lppls.lppls_dataclasses import BubbleStart, ObservationSeries, BubbleType, Peak, BubbleScore
from common.typechecking import TypeCheckBase
from typing import List


class Sornette(TypeCheckBase):
    def __init__(self, observations: ObservationSeries, filter_type, filter_file, should_optimize):
        filter: FilterInterface

        if filter_type == "BitcoinB":
            filter = FilterBitcoin2019B(filter_file)
        else:
            raise Exception("Filter type not supported")

        self.data_fit = DataFit(observations, filter)
        self.bubble_scores = BubbleScores(observations, filter)
        self.should_optimize = should_optimize

    def estimate_prices(self):
        op = self.data_fit.fit(self.data_fit.observations)
        assert op is not None
        return list(np.exp(LPPLSMath.get_log_price_predictions(self.data_fit.observations, op)))

    def plot_fit(self, bubble_start: BubbleStart | None = None) -> None:
        op = self.data_fit.fit(self.data_fit.observations)
        assert op is not None
        self.data_fit.plot_fit(bubble_start, op)

    def compute_bubble_scores(self, **kwargs) -> List[BubbleScore]:
        all_fits = self.data_fit.parallel_compute_t2_recent_fits(**kwargs)
        return self.bubble_scores.compute_bubble_scores(all_fits, self.should_optimize)

    def plot_bubble_scores(self, bubble_scores, ticker, bubble_start, best_end_cluster):
        self.bubble_scores.plot_bubble_scores(bubble_scores, ticker, bubble_start, best_end_cluster)

    def plot_rejection_reasons(self, bubble_scores: List[BubbleScore], ticker: str) -> None:
        self.bubble_scores.plot_rejection_reasons(bubble_scores, ticker)

    def compute_start_time(
        self, observations: ObservationSeries, bubble_type: BubbleType, extremities: List[Peak]
    ) -> BubbleStart:
        # "We impose the constraint that, for a given developing bubble, its start time t1*
        # cannot be earlier than the previous peak, as determined in Figure 1.""
        #
        # Dissection of Bitcoin’s Multiscale Bubble History from January 2012 to February 2018
        dates = observations.get_date_ordinals()
        last_extremity_index = 0
        if len(extremities) > 0:
            last_extremity_index = dates.index(extremities[-1].date_ordinal)
        return BubbleStart(dates[last_extremity_index], bubble_type)
