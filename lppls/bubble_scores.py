from matplotlib import pyplot as plt
import pandas as pd
from count_metrics import CountMetrics
from lppls_defaults import BubbleType, BubbleStart
from pop_dates import Cluster
from matplotlib.lines import Line2D


class BubbleScores:
    def __init__(self, observations, filter):
        self.observations = observations
        self.filter = filter

    def plot_bubble_scores(
        self, bubble_scores, ticker: str, bubble_start: BubbleStart, best_end_cluster: Cluster
    ) -> None:
        fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(18, 10))
        fig.canvas.manager.set_window_title(ticker)
        # if burst_time:
        #     fig.canvas.manager.set_window_subtitle('Burst time: ' + burst_time)

        ord = bubble_scores["time"].astype("int32")
        ts = [pd.Timestamp.fromordinal(d) for d in ord]

        # plot pos bubbles
        ax1_0 = ax1.twinx()
        ax1.plot(ts, bubble_scores["price"], color="black", linewidth=0.75)
        # ax1_0.plot(compatible_date, pos_lst, label='pos bubbles', color='gray', alpha=0.5)
        ax1_0.plot(
            ts,
            bubble_scores["pos_conf"],
            label="bubble indicator (pos)",
            color="red",
            alpha=0.5,
        )

        # plot neg bubbles
        ax2_0 = ax2.twinx()
        ax2.plot(ts, bubble_scores["price"], color="black", linewidth=0.75)
        # ax2_0.plot(compatible_date, neg_lst, label='neg bubbles', color='gray', alpha=0.5)
        ax2_0.plot(
            ts,
            bubble_scores["neg_conf"],
            label="bubble indicator (neg)",
            color="green",
            alpha=0.5,
        )

        # Highlight start_time with a vertical line
        if bubble_start.type == BubbleType.POSITIVE:
            self.draw_bubble_bounds(ax1, bubble_start, bubble_scores, best_end_cluster)
        elif bubble_start.type == BubbleType.NEGATIVE:
            self.draw_bubble_bounds(ax2, bubble_start, bubble_scores, best_end_cluster)

        # set grids
        ax1.grid(which="major", axis="both", linestyle="--")
        ax2.grid(which="major", axis="both", linestyle="--")

        # set labels
        ax1.set_ylabel("ln(p)")
        ax2.set_ylabel("ln(p)")

        ax1_0.set_ylabel("bubble indicator (pos)")
        ax2_0.set_ylabel("bubble indicator (neg)")

        CountMetrics.print_metrics()
        plt.xticks(rotation=45)


    def draw_bubble_bounds(
        self, axis, bubble_start: BubbleStart, bubble_scores, best_end_cluster: Cluster
    ) -> None:
        bubble_start_date = pd.Timestamp.fromordinal(bubble_start.date_ordinal)
        bubble_start_label = (
            f'Start Date ({bubble_start_date.strftime("%Y-%m-%d")})'  # Format the date
        )

        # Draw the vertical line if it's later than the earliest fit
        # Use the 't2' timestamp because these are draws on the bubble score plot
        if int(bubble_scores._fits[0][0]["t2"]) <= bubble_start.date_ordinal:
            axis.axvline(x=bubble_start_date, color="blue", linestyle="--", linewidth=2)
        axis.text(
            bubble_start_date,
            axis.get_ylim()[1],
            bubble_start_label,
            color="blue",
            ha="left",
            va="bottom",
        )

        # Create a custom legend entry for cluster_info
        cluster_legend = [
            Line2D(
                [0],
                [0],
                color="none",
                marker="none",
                markerfacecolor="none",
                label=best_end_cluster.displayCluster(),
            )
        ]

        # Add the custom legend entry to the existing legend
        axis.legend(
            handles=axis.get_legend_handles_labels()[0] + cluster_legend, loc=2, facecolor="white"
        )


    def compute_bubble_scores(self, fits):
        pos_conf_lst = []
        neg_conf_lst = []
        price = []
        ts = []
        _fits = []

        for kps in fits:
            ts.append(kps["t2"])
            price.append(kps["p2"])
            pos_qual_count = 0
            neg_qual_count = 0
            pos_count = 0
            neg_count = 0
            t1_index = kps["t1_index"]
            t2_index = kps["t2_index"]

            for idx, fits in enumerate(kps["windows"]):
                is_qualified, is_positive_bubble = self.filter.check_bubble_fit(
                    fits, self.observations, t1_index, t2_index
                )

                if is_positive_bubble:
                    pos_count += 1
                    if is_qualified:
                        pos_qual_count += 1
                else:
                    neg_count += 1
                    if is_qualified:
                        neg_qual_count += 1

                kps["windows"][idx]["is_qualified"] = is_qualified

            _fits.append(kps["windows"])

            pos_conf = pos_qual_count / pos_count if pos_count > 0 else 0
            neg_conf = neg_qual_count / neg_count if neg_count > 0 else 0
            pos_conf_lst.append(pos_conf)
            neg_conf_lst.append(neg_conf)

        bubble_scores = pd.DataFrame(
            {
                "time": ts,
                "price": price,
                "pos_conf": pos_conf_lst,
                "neg_conf": neg_conf_lst,
                "_fits": _fits,
            }
        )
        return bubble_scores
