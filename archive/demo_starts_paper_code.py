# Python script for computing the Lambda regulariser metric - OLS case.
# Copyright: G. Demos @ ETH-Zurich - Jan.2017

# Copied but heavily refactored from https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3007070

import sys

sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/bubble_bounds"
)
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/common"
)

import numpy as np
from numpy.typing import NDArray
from archive.starts import Starts
from matplotlib import pyplot as plt
from datetime import datetime, timedelta
import pandas as pd


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
        Y += -min_Y + 1  # Add 1 to make the smallest value strictly greater than 0

    return X, Y


def fitDataViaOlsGetBetaAndLine(X: NDArray, Y: NDArray) -> NDArray:
    """Fit synthetic OLS"""
    # Assuming X is a vector and needs to be a matrix with an intercept term
    X_matrix = np.vstack((np.ones(len(X)), X)).T  # Add a column of ones for the intercept
    # Calculate beta_hat using the OLS formula (X'X)^-1X'Y
    beta_hat = np.dot(np.linalg.inv(np.dot(X_matrix.T, X_matrix)), np.dot(X_matrix.T, Y))
    # Calculate predicted Y values
    Y_hat = np.dot(X_matrix, beta_hat)
    return Y_hat


if __name__ == "__main__":
    starts = Starts()
    # Simulate Initial Data
    X, Y = simulateOLS()
    Yhat = fitDataViaOlsGetBetaAndLine(X, Y)  # Get Model fit

    # Calculate the end date as today
    today = datetime.now().date()

    # Generate an array of N consecutive dates ending today
    dates = np.array(
        [pd.Timestamp.toordinal(today - timedelta(days=x)) for x in range(len(Y), 0, -1)]
    )

    starts.plot_all_fit_measures(Y, Yhat, dates)
    plt.show()
