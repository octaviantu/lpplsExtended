from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from lppls_math import LPPLSMath
import math
class BubbleScores:

    def __init__(self, observations, filter):
        self.observations = observations
        self.filter = filter
    

    def plot_bubble_scores(self, known_price_span):
        """
        Args:
            known_price_span (list): result from mp_compute_indicator
            condition_name (str): the name you assigned to the filter condition in your config
            title (str): super title for both subplots
        Returns:
            nothing, should plot the indicator
        """
        known_price_span_df = self.compute_bubble_scores(known_price_span)
        _, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(18, 10))

        ord = known_price_span_df['time'].astype('int32')
        ts = [pd.Timestamp.fromordinal(d) for d in ord]

        # plot pos bubbles
        ax1_0 = ax1.twinx()
        ax1.plot(ts, known_price_span_df['price'], color='black', linewidth=0.75)
        # ax1_0.plot(compatible_date, pos_lst, label='pos bubbles', color='gray', alpha=0.5)
        ax1_0.plot(ts, known_price_span_df['pos_conf'], label='bubble indicator (pos)', color='red', alpha=0.5)

        # plot neg bubbles
        ax2_0 = ax2.twinx()
        ax2.plot(ts, known_price_span_df['price'], color='black', linewidth=0.75)
        # ax2_0.plot(compatible_date, neg_lst, label='neg bubbles', color='gray', alpha=0.5)
        ax2_0.plot(ts, known_price_span_df['neg_conf'], label='bubble indicator (neg)', color='green', alpha=0.5)

        # set grids
        ax1.grid(which='major', axis='both', linestyle='--')
        ax2.grid(which='major', axis='both', linestyle='--')

        # set labels
        ax1.set_ylabel('ln(p)')
        ax2.set_ylabel('ln(p)')

        ax1_0.set_ylabel('bubble indicator (pos)')
        ax2_0.set_ylabel('bubble indicator (neg)')

        ax1_0.legend(loc=2)
        ax2_0.legend(loc=2)

        plt.xticks(rotation=45)


    def compute_bubble_scores(self, known_price_span, filter_conditions_config=None):
        print('self.observation: ', self.observations)

        pos_conf_lst = []
        neg_conf_lst = []
        price = []
        ts = []
        _fits = []

        if filter_conditions_config is None:
            # TODO make configurable again!
            w_min = self.filter.get("w_min")
            w_max = self.filter.get("w_max")
            m_min = self.filter.get("m_min")
            m_max = self.filter.get("m_max")
            O_min = self.filter.get("O_min")
            D_min = self.filter.get("D_min")
        else:
            # TODO parse user provided conditions
            pass

        for kps in known_price_span:
            ts.append(kps['t2'])
            price.append(kps['p2'])
            pos_qual_count = 0
            neg_qual_count = 0
            pos_count = 0
            neg_count = 0
            t1_index = kps['t1_index']
            t2_index = kps['t2_index']

            for idx, fits in enumerate(kps['windows']):
                t1 = fits['t1']
                t2 = fits['t2']
                tc = fits['tc']
                m = fits['m']
                w = fits['w']
                a = fits['b']
                b = fits['b']
                c = fits['c']
                c1 = fits['c1']
                c2 = fits['c2']
                O = fits['O']
                D = fits['D']

                t_delta = t2 - t1                
                t_delta_lower = t_delta * self.filter.get("tc_delta_min")
                t_delta_upper = t_delta * self.filter.get("tc_delta_max")

                prices_in_range = True
                for i in range(t1_index, t2_index):
                    t, p = self.observations[:, i]
                    predicted_price = np.exp(LPPLSMath.lppls(t, tc, m, w, a, b, c1, c2))
                    if not predicted_price:
                        prices_in_range = False
                        break
            
                    predictionError = abs(np.exp(p) - predicted_price)/predicted_price
                    # print(f't: {t}, tc: {tc}, m: {m}, w: {w}, a: {a}, b: {b}, c1: {c1}, c2: {c2}, p: {p}, predicted_price: {predicted_price}')
                    # print('predictionError: ', predictionError)

                    if predictionError > self.filter.get("relative_error_max"):
                        prices_in_range = False
                        break

                if prices_in_range:
                    print('All prices in range!!')


                tc_in_range = max(t1, t2 - t_delta_lower) < tc < t2 + t_delta_upper
                m_in_range = m_min < m < m_max
                w_in_range = w_min < w < w_max

                if b != 0 and c != 0:
                    O = O
                else:
                    O = np.inf

                O_in_range = O > O_min
                D_in_range = D > D_min  # if m > 0 and w > 0 else False

                if tc_in_range and m_in_range and w_in_range and O_in_range and D_in_range and prices_in_range:
                    is_qualified = True
                else:
                    is_qualified = False

                if b < 0:
                    pos_count += 1
                    if is_qualified:
                        pos_qual_count += 1
                if b > 0:
                    neg_count += 1
                    if is_qualified:
                        neg_qual_count += 1
                # add this to known_price_span to make life easier
                kps['windows'][idx]['is_qualified'] = is_qualified

            _fits.append(kps['windows'])

            pos_conf = pos_qual_count / pos_count if pos_count > 0 else 0
            neg_conf = neg_qual_count / neg_count if neg_count > 0 else 0
            pos_conf_lst.append(pos_conf)
            neg_conf_lst.append(neg_conf)

        print(f'pos_conf_lst: {pos_conf_lst}, neg_conf_lst: {neg_conf_lst}')

        known_price_span_df = pd.DataFrame({
            'time': ts,
            'price': price,
            'pos_conf': pos_conf_lst,
            'neg_conf': neg_conf_lst,
            '_fits': _fits,
        })
        return known_price_span_df
