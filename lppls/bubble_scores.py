from matplotlib import pyplot as plt
import numpy as np
from count_metrics import CountMetrics
from lppls_dataclasses import (
    BubbleType,
    BubbleStart,
    ObservationSeries,
    IntervalFits,
    BubbleScore,
    RejectionReason,
)
from pop_dates import Cluster
from matplotlib.lines import Line2D
from filter_interface import FilterInterface
from typing import List
from date_utils import DateUtils as du
import matplotlib.dates as mdates
from typechecking import TypeCheckBase


class BubbleScores(TypeCheckBase):
    def __init__(self, observations: ObservationSeries, filter: FilterInterface):
        self.observations = observations
        self.filter = filter

    def plot_bubble_scores(
        self,
        bubble_scores: List[BubbleScore],
        ticker: str,
        bubble_start: BubbleStart,
        best_end_cluster: Cluster,
    ) -> None:
        fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(18, 10))
        fig.canvas.manager.set_window_title(ticker)

        dates = [du.ordinal_to_date(bs.t2) for bs in bubble_scores]
        log_prices = [bs.log_price for bs in bubble_scores]
        pos_conf = [bs.pos_conf for bs in bubble_scores]
        neg_conf = [bs.neg_conf for bs in bubble_scores]

        # plot pos bubbles
        ax1_0 = ax1.twinx()
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
        ax1.plot(dates, log_prices, color="black", linewidth=0.75)
        ax1_0.plot(
            dates,
            pos_conf,
            label="bubble indicator (pos)",
            color="red",
            alpha=0.5,
        )

        # plot neg bubbles
        ax2_0 = ax2.twinx()
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
        ax2.plot(dates, log_prices, color="black", linewidth=0.75)
        ax2_0.plot(
            dates,
            neg_conf,
            label="bubble indicator (neg)",
            color="green",
            alpha=0.5,
        )

        earliest_end_date = bubble_scores[0].t2
        # Highlight start_time with a vertical line
        if bubble_start.type == BubbleType.POSITIVE:
            self.draw_bubble_bounds(ax1, bubble_start, earliest_end_date, best_end_cluster, dates)
        elif bubble_start.type == BubbleType.NEGATIVE:
            self.draw_bubble_bounds(ax2, bubble_start, earliest_end_date, best_end_cluster, dates)

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

    def plot_rejection_reasons(self, bubble_scores: List[BubbleScore], ticker: str) -> None:
        fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(18, 10))
        fig.canvas.manager.set_window_title(ticker)

        # Prepare data for plotting
        dates = [du.ordinal_to_date(bs.t2) for bs in bubble_scores]
        log_prices = [bs.log_price for bs in bubble_scores]
        pos_conf = [100 * bs.pos_conf for bs in bubble_scores]
        neg_conf = [100 * bs.neg_conf for bs in bubble_scores]

        # Plot log prices and pos/neg bubbles
        ax1.plot(dates, log_prices, color="black", linewidth=2)
        ax1_0 = ax1.twinx()
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
        ax1_0.plot(dates, pos_conf, label="bubble indicator (pos)", color="red", linewidth=2)
        ax2.plot(dates, log_prices, color="black", linewidth=2)
        ax2_0 = ax2.twinx()
        ax2.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
        ax2_0.plot(dates, neg_conf, label="bubble indicator (neg)", color="green", linewidth=2)

        # Calculate and plot rejection reasons
        colors = ["blue", "orange", "purple", "brown", "cyan", "gray"]
        rejection_percentages = {reason: [] for reason in RejectionReason}
        for bs in bubble_scores:
            total_intervals = len(bs.optimized_intervals)
            counts = {reason: 0 for reason in RejectionReason}
            for interval in bs.optimized_intervals:
                for reason in interval.bubble_fit.rejection_reasons:
                    counts[reason] += 1
            for reason, count in counts.items():
                rejection_percentages[reason].append(
                    (count / total_intervals) * 100 if total_intervals > 0 else 0
                )

        for i, (reason, percentages) in enumerate(rejection_percentages.items()):
            color = colors[i % len(colors)]  # Cycle through colors
            ax1_0.plot(
                dates,
                percentages,
                label=f"rejection reason: {reason.name}",
                linestyle="--",
                color=color,
            )
            ax2_0.plot(
                dates,
                percentages,
                label=f"rejection reason: {reason.name}",
                linestyle="--",
                color=color,
            )

        # Set grids, labels, and legends
        ax1.grid(which="major", axis="both", linestyle="--")
        ax2.grid(which="major", axis="both", linestyle="--")
        ax1.set_ylabel("ln(p)")
        ax2.set_ylabel("ln(p)")
        ax1_0.set_ylabel("bubble indicator (pos) / Rejection Reason %")
        ax2_0.set_ylabel("bubble indicator (neg) / Rejection Reason %")
        ax1_0.legend(loc="upper left")
        ax2_0.legend(loc="upper left")
        plt.xticks(rotation=45)

    def draw_bubble_bounds(
        self,
        axis,
        bubble_start: BubbleStart,
        earliest_end_date: int,
        best_end_cluster: Cluster,
        dates: List[str],
    ) -> None:
        bubble_start_date = du.ordinal_to_date(bubble_start.date_ordinal)
        bubble_start_label = f"Start Date ({bubble_start_date})"  # Format the date
        closest_date = dates[np.searchsorted(dates, bubble_start_date)]

        # Draw the vertical line if it's later than the earliest fit
        if earliest_end_date <= bubble_start.date_ordinal:
            axis.axvline(x=closest_date, color="blue", linestyle="--", linewidth=2)
        axis.text(
            closest_date,
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

    def compute_bubble_scores(
        self, all_fits: List[IntervalFits], should_optimize: bool
    ) -> List[BubbleScore]:
        bubble_scores = []

        for fit in all_fits:
            pos_qual_count = 0
            neg_qual_count = 0
            pos_count = 0
            neg_count = 0

            for idx, optimizedInterval in enumerate(fit.optimized_intervals):
                bubble_fit = self.filter.check_bubble_fit(
                    optimizedInterval, self.observations, should_optimize
                )

                if bubble_fit.type == BubbleType.POSITIVE:
                    pos_count += 1
                    if not bubble_fit.rejection_reasons:
                        pos_qual_count += 1
                else:
                    neg_count += 1
                    if not bubble_fit.rejection_reasons:
                        neg_qual_count += 1

                fit.optimized_intervals[idx].bubble_fit = bubble_fit

            bubble_scores.append(
                BubbleScore(
                    fit.t2,
                    np.log(fit.p2),
                    pos_qual_count / pos_count if pos_count > 0 else 0,
                    neg_qual_count / neg_count if neg_count > 0 else 0,
                    fit.optimized_intervals,
                )
            )

        return bubble_scores
