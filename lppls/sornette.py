import sys
sys.path.append("/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/bubble_bounds")

import numpy as np
from count_metrics import CountMetrics
from bubble_scores import BubbleScores
from data_fit import DataFit
from filter_shanghai import FilterShanghai
from filter_bitcoin2019B import FilterBitcoin2019B
from filter_swiss import FilterSwiss
from filimonov_plot import FilimonovPlot
from lppls_math import LPPLSMath
from bounds import Bounds
from lppls_defaults import MAX_SEARCHES

class Sornette:
    def __init__(self, observations, filter_type, filter_file):
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
        self.bounds = Bounds()


    def plot_fit(self):
        self.data_fit.plot_fit(**self.lppls_equation_terms())

    def parallel_compute_t2_fits(self, **kwargs):
        return self.data_fit.parallel_compute_t2_fits(**kwargs)

    def parallel_compute_t2_recent_fits(self, **kwargs):
        return self.data_fit.parallel_compute_t2_recent_fits(**kwargs)

    def plot_bubble_scores(self, res_filtered, ticker, bubble_start):
        self.bubble_scores.plot_bubble_scores(res_filtered, ticker, bubble_start)

    def plot_filimonov(self):
        self.filimonov_plot.plot_optimum(self.data_fit.observations)

    def compute_start_time(self, times, actual_prices, bubble_type, extremities):
        [expected_log_prices, _] = LPPLSMath.get_log_price_predictions(
            [times, actual_prices], **self.lppls_equation_terms()
        )
        expected_prices = [np.exp(p) for p in expected_log_prices]
        return self.bounds.compute_start_time(times, actual_prices, expected_prices, bubble_type, extremities)

    def lppls_equation_terms(self):
        [_, lppls_coef] = self.data_fit.fit(MAX_SEARCHES, self.data_fit.observations)
        return {
            k: lppls_coef[k] for k in ["tc", "m", "w", "a", "b", "c1", "c2"]
        }
