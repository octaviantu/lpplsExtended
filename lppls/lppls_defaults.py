from enum import Enum
from dataclasses import dataclass

LARGEST_WINDOW_SIZE = 150  # working days in 7 months
SMALLEST_WINDOW_SIZE = 30

LARGEST_WINDOW_SIZE_STRICT = 180
SMALLEST_WINDOW_SIZE_STRICT = 20

RECENT_VISIBLE_WINDOWS = 200

# t1 is set to 5 in the Shanghai paper but there they move it between 125 and 750
T1_STEP = 2
T1_STEP_STRICT = 1

# t2 of 5 is used in the Bitcoin paper
T2_STEP = 1

MAX_SEARCHES = 25

# Lomb test from:
# Real-time Prediction of Bitcoin Bubble Crashes (2019)
# Authors: Min Shu, Wei Zhu
SIGNIFICANCE_LEVEL = 0.05


# windows that are close to the end of the data, to see if there is a recent bubble
# RECENT_RELEVANT_WINDOWS = 20


# From 'Dissection of Bitcoin’s Multiscale Bubble History from January 2012 to February 2018' - Demos, Sornette
# The ratio of windows over which a value is min/max for us to consider it a peak
PEAK_THRESHOLD = 0.95

# In the paper epsilon is within [0.1, 5] with step 0.1 but I made it bigger, otherwise too many peaks are highlighted.
EPSILON_RANGE_START = 0.2
EPSILON_RANGE_END = 10
EPSILON_STEP = 0.2
W_RANGE_START = 10
W_RANGE_END = 60
W_STEP = 5


class BubbleType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


@dataclass
class BubbleStart:
    date_ordinal: int
    type: BubbleType

@dataclass
class Peak:
    type: BubbleType
    date_ordinal: int
    score: float

