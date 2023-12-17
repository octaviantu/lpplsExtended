LARGEST_WINDOW_SIZE = 150  # working days in 7 months
SMALLEST_WINDOW_SIZE = 30

RECENT_VISIBLE_WINDOWS = 200

# t1 is set to 5 in the Shanghai paper but there they move it between 125 and 750
T1_STEP = 2

# t2 of 5 is used in the Bitcoin paper
T2_STEP = 1

MAX_SEARCHES = 25
TRIES_TO_GET_MINIMUM = 2 # A value of 7 removes most spuriosu results

# Lomb test from:
# Real-time Prediction of Bitcoin Bubble Crashes (2019)
# Authors: Min Shu, Wei Zhu
SIGNIFICANCE_LEVEL = 0.05
# This would take out too many fits if smaller.
# It's also never mentioned by Sornette in his book so I rely on it less.
ADF_SIGNIFICANCE_LEVEL = 0.4

# From 'Dissection of Bitcoin’s Multiscale Bubble History from January 2012 to February 2018' - Demos, Sornette
# The ratio of windows over which a value is min/max for us to consider it a peak
PEAK_THRESHOLD = 0.95

# In the paper epsilon is within [0.1, 5] with step 0.1 but I made it bigger, otherwise too many peaks are highlighted.
EPSILON_RANGE_START = 0.2
EPSILON_RANGE_END = 10
EPSILON_STEP = 0.2
# In the paper w is within [10, 60] but I made the range bigger to avoid peaks
# that come on a downtrend(see SMR 2021-2023).
W_RANGE_START = 10
W_RANGE_END = 90
W_STEP = 5


# Constraints from appendix E from:
# Dissection of Bitcoin’s Multiscale Bubble History from January 2012 to February 2018
MIN_NR_CLUSTERS = 2
MAX_NR_CLUSTERS = 10


OPTIMIZE_DISQUALIFY_PRICE_DIFF = 0.25
OPTIMIZE_DISQUALIFY_TIME = 8 * 22  # 8 months, with working days
OPTIMIZE_T1_STEP = 4


# These could be used for a stricter fit.However, that is not implemented at present.
LARGEST_WINDOW_SIZE_STRICT = 180
SMALLEST_WINDOW_SIZE_STRICT = 20
T1_STEP_STRICT = 1
