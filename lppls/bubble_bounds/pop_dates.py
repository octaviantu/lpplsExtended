# Implements Appendix E from:
# Dissection of Bitcoin’s Multiscale Bubble History from January 2012 to February 2018
# J.C. Gerlach† , G. Demos†, D. Sornette†♮

from typing import List
from lppls_defaults import MIN_NR_CLUSTERS, MAX_NR_CLUSTERS
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import numpy as np
from lppls_dataclasses import BubbleStart, BubbleScore
from db_dataclasses import PopRange
from date_utils import DateUtils as du
from typechecking import TypeCheckBase

MIN_POINTS_CLUSTER_RATIO = 3
# Only extract windows from these last days
LAST_DAYS_WITH_DATA = 8

# Approximating 1 month as 30 days
MAX_POP_TIMES_DISPERSION = 6 * 30  # More than this, and the data is too imprecise
MAX_LAG_FROM_TODAY = 3 * 30  # More than this, and I can not short/buy puts


class Cluster(TypeCheckBase):
    def __init__(self, mean_pop_dates: List[int] | None = None, silhouette: float | None = None):
        if not mean_pop_dates or not silhouette:
            self.is_valid = False
            self.mean_pop_dates = []
            self.silhouette = 0.0
        else:
            self.is_valid = True
            self.mean_pop_dates = sorted(mean_pop_dates)
            self.silhouette = silhouette

    def silhouette_score(self) -> str:
        if not self.is_valid:
            return "Invalid cluster"
        return str(self.silhouette)

    def pop_dates_count(self) -> str:
        if not self.is_valid:
            return "Invalid cluster"
        return str(len(self.mean_pop_dates))

    def displayCluster(self):
        if not self.is_valid:
            return "Invalid cluster"
        format_pop_dates = [du.ordinal_to_date(d) for d in self.mean_pop_dates]
        return (
            f"Clustered in {format_pop_dates} with silhouette: {self.silhouette:.2f} (1 is optimal)"
        )

    def give_pop_dates_range(self) -> PopRange | None:
        if not self.is_valid or not self.mean_pop_dates:
            return None

        first_pop_date, last_pop_date = self.mean_pop_dates[0], self.mean_pop_dates[-1]

        # If pop dates are too dispersed, they are not actionable.
        if last_pop_date - first_pop_date > MAX_POP_TIMES_DISPERSION:
            return None
        if last_pop_date > du.today_ordinal() + MAX_LAG_FROM_TODAY:
            return None

        return PopRange(first_pop_date, last_pop_date)


class PopDates(TypeCheckBase):
    def compute_bubble_end_cluster(
        self, start_time: BubbleStart, bubble_scores: List[BubbleScore]
    ) -> Cluster:
        tcs = []

        # Get the ordinal dates for the last LAST_DAYS_WITH_DATA days
        last_days_ordinals = [du.today_ordinal() - i for i in range(LAST_DAYS_WITH_DATA, -1, -1)]

        for bubble_score in bubble_scores:
            if bubble_score.t2 < last_days_ordinals[0]:
                continue
            for oi in bubble_score.optimized_intervals:
                if not oi.bubble_fit.rejection_reasons and oi.t1 >= start_time.date_ordinal:
                    tcs.append([oi.optimized_params.tc])  # need 2D array

        print("Number of tcs considered in clustering: ", len(tcs))
        if len(tcs) < MIN_POINTS_CLUSTER_RATIO * MIN_NR_CLUSTERS:
            return Cluster()

        clusters = []
        for k in range(MIN_NR_CLUSTERS, min(len(tcs), MAX_NR_CLUSTERS + 1)):
            kmeans = KMeans(n_clusters=k, n_init=10)
            kmeans.fit(tcs)
            labels = kmeans.labels_
            silhouette_avg = silhouette_score(tcs, labels)

            rounded_centers = np.round(kmeans.cluster_centers_, 0).astype(int)
            list_of_centers = rounded_centers.flatten().tolist()
            clusters.append(Cluster(list_of_centers, silhouette_avg))

            print(f"For n_clusters = {k}, the average silhouette_score is : {silhouette_avg}")

        best_cluster = min(clusters, key=lambda c: 1 - c.silhouette)
        return best_cluster
