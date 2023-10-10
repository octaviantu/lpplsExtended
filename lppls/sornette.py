from bubble_scores import BubbleScores
from data_fit import DataFit
from filter_shanghai import FilterShanghai

class Sornette:
    def __init__(self, observations, filter_type, filter_file):
        if filter_type == 'Shanghai':
            filter = FilterShanghai(filter_file)
        else:
            raise Exception('Filter type not supported')
    
        self.data_fit = DataFit(observations, filter)
        self.bubble_scores = BubbleScores(observations, filter)
        
    def fit(self, max_searches):
        [_, self.lppls_coef] = self.data_fit.fit(max_searches, self.data_fit.observations)
        
    def plot_fit(self):
        self.data_fit.plot_fit(self.lppls_coef)

    def mp_compute_t1_fits(self, **kwargs):
        return self.data_fit.mp_compute_t1_fits(**kwargs)

    def plot_bubble_scores(self, res_filtered):
        self.bubble_scores.plot_bubble_scores(res_filtered)
