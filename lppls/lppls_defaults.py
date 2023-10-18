LARGEST_WINDOW_SIZE = 150  # working days in 7 months
SMALLEST_WINDOW_SIZE = 30

# t1 is set to 5 in the Shanghai paper but there they move it between 125 and 750
T1_STEP = 2
# t2 of 5 is used in the Bitcoin paper
T2_STEP = 1

MAX_SEARCHES = 25

# Lomb test from:
# Real-time Prediction of Bitcoin Bubble Crashes (2019)
# Authors: Min Shu, Wei Zhu
SIGNIFICANCE_LEVEL = 0.05


# windows that are close to the end of the data, to see if there is a recent bubble
# RECENT_RELEVANT_WINDOWS = 20
