import numpy as np
from count_metrics import CountMetrics
from bubble_scores import BubbleScores
from data_fit import DataFit
from filter_shanghai import FilterShanghai
from filter_bitcoin2019B import FilterBitcoin2019B
from filter_swiss import FilterSwiss
from filter_interface import FilterInterface
from filimonov_plot import FilimonovPlot
from lppls_math import LPPLSMath
from lppls_defaults import MAX_SEARCHES
from starts import Starts
from lppls_dataclasses import BubbleStart, ObservationSeries


class Sornette:
    def __init__(self, observations: ObservationSeries, filter_type, filter_file):
        filter: FilterInterface

        if filter_type == "Shanghai":
            filter = FilterShanghai(filter_file)
        elif filter_type == "BitcoinB":
            filter = FilterBitcoin2019B(filter_file)
        elif filter_type == "Swiss":
            filter = FilterSwiss(filter_file)
        else:
            raise Exception("Filter type not supported")

        self.data_fit = DataFit(observations, filter)
        self.bubble_scores = BubbleScores(observations, filter)
        self.filimonov_plot = FilimonovPlot()
        CountMetrics.reset()
        self.starts = Starts()

    def estimate_prices(self):
        op = self.data_fit.fit(MAX_SEARCHES, self.data_fit.observations)
        assert op is not None
        return np.exp(LPPLSMath.get_log_price_predictions(self.data_fit.observations, op))

    def plot_fit(self, bubble_start: BubbleStart | None = None) -> None:
        op = self.data_fit.fit(MAX_SEARCHES, self.data_fit.observations)
        assert op is not None
        self.data_fit.plot_fit(bubble_start, op)

    def parallel_compute_t2_fits(self, **kwargs):
        return self.data_fit.parallel_compute_t2_fits(**kwargs)

    def compute_bubble_scores(self, **kwargs):
        all_fits = self.data_fit.parallel_compute_t2_recent_fits(**kwargs)
        return self.bubble_scores.compute_bubble_scores(all_fits)

    def plot_bubble_scores(self, bubble_scores, ticker, bubble_start, best_end_cluster):
        self.bubble_scores.plot_bubble_scores(bubble_scores, ticker, bubble_start, best_end_cluster)

    def plot_filimonov(self):
        self.filimonov_plot.plot_optimum(self.data_fit.observations)

    def compute_start_time(
        self, observations: ObservationSeries, bubble_type, extremities
    ) -> BubbleStart:
        op = self.data_fit.fit(MAX_SEARCHES, self.data_fit.observations)
        assert op is not None
        expected_prices = np.exp(LPPLSMath.get_log_price_predictions(observations, op))
        return self.starts.compute_start_time(
            observations.get_date_ordinals(),
            observations.get_prices(),
            expected_prices,
            bubble_type,
            extremities,
        )
