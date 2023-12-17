import sys

sys.path.append("/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls")
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/bubble_bounds"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/common"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/metrics"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/prices_db_management"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/previous_performance"
)

from matplotlib import pyplot as plt
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from lppls_dataclasses import BubbleScore, BubbleType, Observation, ObservationSeries
from peaks import Peaks
import psycopg2
from date_utils import DateUtils as du
from lppls_defaults import (
    LARGEST_WINDOW_SIZE,
    SMALLEST_WINDOW_SIZE,
    T1_STEP,
    T2_STEP,
    MAX_SEARCHES,
    OPTIMIZE_T1_STEP,
)
from sornette import Sornette
from typing import List
from starts import Starts
from lppls_math import LPPLSMath
import numpy as np
from data_fit import DataFit
from filter_bitcoin2019B import FilterBitcoin2019B

BUBBLE_THRESHOLD = 0.25
# windows that are close to the end of the data, to see if there is a recent bubble
RECENT_RELEVANT_WINDOWS = 5
LIMIT_OF_MOST_TRADED_COMPANIES = 250


def get_connection():
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
        )


def get_bubble_scores(sornette: Sornette, recent_windows: int, t1_step: int
) -> List[BubbleScore]:
    return sornette.compute_bubble_scores(
        workers=8,
        recent_windows=recent_windows,
        window_size=LARGEST_WINDOW_SIZE,
        smallest_window_size=SMALLEST_WINDOW_SIZE,
        t1_increment=t1_step,
        t2_increment=T2_STEP,
        max_searches=MAX_SEARCHES,
    )


def is_in_bubble_state(
    observations: ObservationSeries,
    filter_type: str,
    filter_file: str,
    should_optimize: bool,
) -> tuple[BubbleType | None, List[float], Sornette]:
    sornette = Sornette(observations, filter_type, filter_file, should_optimize)

    relevant_windows = 1 if should_optimize else RECENT_RELEVANT_WINDOWS
    t1_step = T1_STEP if should_optimize else OPTIMIZE_T1_STEP
    bubble_scores = get_bubble_scores(sornette, relevant_windows, t1_step)
    pos_conf = [bs.pos_conf for bs in bubble_scores]
    neg_conf = [bs.neg_conf for bs in bubble_scores]

    if max(pos_conf) > BUBBLE_THRESHOLD:
        return BubbleType.POSITIVE, pos_conf, sornette
    elif max(neg_conf) > BUBBLE_THRESHOLD:
        return BubbleType.NEGATIVE, neg_conf, sornette

    return None, [0.0], sornette


if __name__ == "__main__":
    test_date = du.days_ago(740)
    SPECIFIC_TICKERS = ["TSLA"]

    conn = get_connection()
    cursor = conn.cursor()
    for ticker in SPECIFIC_TICKERS:
        # Never select today - we run this before the market opens
        query = f"SELECT date, close_price FROM pricing_history WHERE ticker='{ticker}' AND date < '{test_date}' ORDER BY date ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        observations = ObservationSeries(
            [Observation(price=row[1], date_ordinal=row[0].toordinal()) for row in rows]
        )

        bubble_type, _, sornette = is_in_bubble_state(
            observations,
            "BitcoinB",
            "./lppls/conf/demos2015_filter.json",
            should_optimize=True,
        )
        if not bubble_type:
            # TODO(octaviant) - make it back to be None
            bubble_type = BubbleType.POSITIVE

        drawups, drawdowns, _ = Peaks(observations, ticker).plot_peaks(test_date)
        extremities = drawups if bubble_type == BubbleType.POSITIVE else drawdowns
        last_extremity_index = 0
        for i in range(len(observations) - 1, -1, -1):
            if observations[i].date_ordinal == extremities[-1].date_ordinal:
                last_extremity_index = i
                break
        observations = observations[last_extremity_index:]

        filter = FilterBitcoin2019B("./lppls/conf/demos2015_filter.json")
        data_fit = DataFit(observations, filter)
        op = filter.fit(MAX_SEARCHES, observations)
        data_fit.plot_fit(None, op)

        # expected_prices = LPPLSMath.get_log_price_predictions(observations, op)
        expected_prices = list(np.exp(LPPLSMath.get_log_price_predictions(observations, op)))

        print(f'Dates bounds: {du.ordinal_to_date(observations[0].date_ordinal)} - {du.ordinal_to_date(observations[-1].date_ordinal)}')
        starts = Starts()
        # starts.plot_all_fit_measures(observations.get_log_prices(), expected_prices, observations.get_date_ordinals())
        starts.plot_all_fit_measures(observations, filter)

        # starts.plot_fits_after_last_extremity(
        #     observations.get_date_ordinals(),
        #     observations.get_prices(),
        #     expected_prices,
        #     drawups if bubble_type == BubbleType.POSITIVE else drawdowns,
        # )
        
        # bubble_start = sornette.compute_start_time(
        #     observations,
        #     bubble_type,
        #     drawups if bubble_type == BubbleType.POSITIVE else drawdowns,
        # )
        # sornette.plot_fit(bubble_start)
        # bubble_scores = get_bubble_scores(sornette, 50, T1_STEP)
        # best_end_cluster = PopDates().compute_bubble_end_cluster(
        #     bubble_start, bubble_scores, test_date
        # )

        # sornette.plot_bubble_scores(bubble_scores, ticker, bubble_start, best_end_cluster)

        # sornette.plot_rejection_reasons(bubble_scores, ticker)
    plt.show(block=True)
