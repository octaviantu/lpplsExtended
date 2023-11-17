# Implements Appendix E from:
# Dissection of Bitcoin’s Multiscale Bubble History from January 2012 to February 2018
# J.C. Gerlach† , G. Demos†, D. Sornette†♮

from typing import List
from lppls_defaults import MIN_NR_CLUSTERS, MAX_NR_CLUSTERS
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from lppls_defaults import BubbleStart


class Cluster:
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
        format_pop_dates = [
            pd.Timestamp.fromordinal(d).strftime("%Y-%m-%d") for d in self.mean_pop_dates
        ]
        return (
            f"Clustered in {format_pop_dates} with silhouette: {self.silhouette:.2f} (1 is optimal)"
        )


    def give_one_pop_date(self) -> int | None:
        if not self.is_valid or not self.mean_pop_dates:
            return None

        # Convert ordinals to datetime objects
        datetime_pop_dates = [datetime.fromordinal(d) for d in self.mean_pop_dates]

        if datetime_pop_dates[-1] - datetime_pop_dates[0] <= timedelta(days=6*30):  # Approximating 1 month as 30 days
            return self.mean_pop_dates[0]
        else:
            return None



MIN_POINTS_CLUSTER_RATIO = 3

# Only extract windows from these last days
LAST_DAYS_WITH_DATA = 8


class PopDates:
    def compute_bubble_end_cluster(self, start_time: BubbleStart, bubble_scores) -> Cluster:
        tcs = []

        # Get today's date in ordinal form
        today_ordinal = pd.Timestamp(datetime.today()).toordinal()
        # Get the ordinal dates for the last LAST_DAYS_WITH_DATA days
        last_days_ordinals = [today_ordinal - i for i in range(LAST_DAYS_WITH_DATA)]

        for fit in bubble_scores["_fits"]:
            for window in fit:
                # TODO(octaviant) - store window['t2'] as int and don't convert here
                if (
                    window["is_qualified"]
                    and window["t1"] >= start_time.date_ordinal
                    and int(window["t2"]) in last_days_ordinals
                ):
                    tcs.append([window["tc"]])  # need 2D array

        print("Number of tcs considered in clustering: ", len(tcs))
        if len(tcs) < MIN_POINTS_CLUSTER_RATIO * MAX_NR_CLUSTERS:
            return Cluster()

        clusters = []
        for k in range(MIN_NR_CLUSTERS, MAX_NR_CLUSTERS + 1):
            kmeans = KMeans(n_clusters=k)
            kmeans.fit(tcs)
            labels = kmeans.labels_
            silhouette_avg = silhouette_score(tcs, labels)

            rounded_centers = np.round(kmeans.cluster_centers_, 0).astype(int)
            list_of_centers = rounded_centers.flatten().tolist()
            clusters.append(Cluster(list_of_centers, silhouette_avg))

            print(f"For n_clusters = {k}, the average silhouette_score is : {silhouette_avg}")

        best_cluster = min(clusters, key=lambda c: 1 - c.silhouette)
        return best_cluster
