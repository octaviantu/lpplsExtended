from bubble_scores import BubbleScores
from data_fit import DataFit
import data_loader

class Sornette:
    def __init__(self, observations, filter_file='./lppls/conf/default_filter.json'):
        filter = data_loader.load_config(filter_file)
        self.data_fit = DataFit(observations, filter)
        self.bubble_scores = BubbleScores(filter)
        
    def fit(self, max_searches):
        self.lppls_coef = self.data_fit.fit(max_searches, self.data_fit.observations)
        
    def plot_fit(self):
        self.data_fit.plot_fit(self.lppls_coef)

    def mp_compute_nested_fits(self, **kwargs):
        return self.data_fit.mp_compute_nested_fits(**kwargs)

    def plot_bubble_scores(self, res_filtered):
        self.bubble_scores.plot_bubble_scores(res_filtered)
