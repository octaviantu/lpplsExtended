from matplotlib import pyplot as plt
import pandas as pd

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


    def compute_bubble_scores(self, known_price_span):
        pos_conf_lst = []
        neg_conf_lst = []
        price = []
        ts = []
        _fits = []


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
                
                is_qualified, is_positive_bubble = self.filter.check_bubble_fit(fits, self.observations, t1_index, t2_index)
            
                if is_positive_bubble:
                    pos_count += 1
                    if is_qualified:
                        pos_qual_count += 1
                else:
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
