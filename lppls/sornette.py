from count_metrics import CountMetrics
from bubble_scores import BubbleScores
from data_fit import DataFit
from filter_shanghai import FilterShanghai
from filter_bitcoin2019B import FilterBitcoin2019B
from filter_swiss import FilterSwiss
from filimonov_plot import FilimonovPlot


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

    def fit(self, max_searches):
        [_, self.lppls_coef] = self.data_fit.fit(max_searches, self.data_fit.observations)

    def plot_fit(self):
        lppls_equation_terms = {
            k: self.lppls_coef[k] for k in ["tc", "m", "w", "a", "b", "c1", "c2"]
        }
        self.data_fit.plot_fit(**lppls_equation_terms)

    def parallel_compute_t2_fits(self, **kwargs):
        return self.data_fit.parallel_compute_t2_fits(**kwargs)

    def parallel_compute_t2_recent_fits(self, **kwargs):
        return self.data_fit.parallel_compute_t2_recent_fits(**kwargs)

    def plot_bubble_scores(self, res_filtered, ticker):
        self.bubble_scores.plot_bubble_scores(res_filtered, ticker)

    def plot_filimonov(self):
        self.filimonov_plot.plot_optimum(self.data_fit.observations)
