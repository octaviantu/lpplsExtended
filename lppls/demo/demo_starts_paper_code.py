# Python script for computing the Lambda regulariser metric - OLS case.
# Copyright: G. Demos @ ETH-Zurich - Jan.2017

# Copied but heavily refactored from https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3007070

import sys
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/bubble_bounds"
)

import numpy as np
from numpy.typing import NDArray
from starts import Starts


def simulateOLS() -> tuple[NDArray, NDArray]:
    """Generate synthetic OLS as presented in the paper."""
    nobs: int = 200
    X: NDArray = np.arange(0, nobs, 1)
    e: NDArray = np.random.normal(0, 10, nobs)
    beta: float = 0.5
    Y: NDArray = np.array([beta * X[i] + e[i] for i in range(len(X))])
    Y[0:100] += 4 * e[0:100]
    Y[100:200] *= 8

    # Ensure all elements of Y are larger than 0
    min_Y = Y.min()
    if min_Y < 0:
        Y += (-min_Y + 1)  # Add 1 to make the smallest value strictly greater than 0

    return X, Y


if __name__ == "__main__":
    starts = Starts()
    # Simulate Initial Data
    X, Y = simulateOLS()
    
    starts.plot_all_fit_measures(X, Y)
