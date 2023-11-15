# Implements Appendix E from:
# Dissection of Bitcoin’s Multiscale Bubble History from January 2012 to February 2018
# J.C. Gerlach† , G. Demos†, D. Sornette†♮

from typing import List
from lppls_defaults import MIN_NR_CLUSTERS, MAX_NR_CLUSTERS
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import pandas as pd
from dataclasses import dataclass
import numpy as np

@dataclass
class Cluster:
    mean_pop_dates: List[int]
    silhouette: float

    def format_mean_pop_dates(self) -> List[str]:
        return [pd.Timestamp.fromordinal(d).strftime('%Y-%m-%d') for d in self.mean_pop_dates] 


class PopDates:

    def compute_bubble_end_time(self, start_time: int, fits) -> List[Cluster]:
        tcs = []
        for fit in fits:
            if fit['t1'] >= start_time.date_ordinal:
                # TODO(octaviant) - maybe take into account only qualified windows
                for window in fit['windows']:
                    tcs.append([window['tc']]) # need 2D array


        clusters = []
        for k in range(MIN_NR_CLUSTERS, MAX_NR_CLUSTERS + 1):
            kmeans = KMeans(n_clusters=k)
            kmeans.fit(tcs)
            labels = kmeans.labels_
            silhouette_avg = silhouette_score(tcs, labels)

            rounded_centers = np.round(kmeans.cluster_centers_, 0).astype(int)
            list_of_centers= rounded_centers.flatten().tolist()
            clusters.append(Cluster(list_of_centers, silhouette_avg))

            print(f'For n_clusters = {k}, the average silhouette_score is : {silhouette_avg}')

        best_cluster = min(clusters, key=lambda c: 1 - c.silhouette)

        return best_cluster
