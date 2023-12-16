# NOT USED - RUBBISH
# The models will always be more overfitted for smaller windows.
# The linear regression is DUMB.
# The paper describing it 'Lagrange regularisation approach ...' by Demos, Sornette
# has horrible code and it's unclear on page 3 wether we should add or subtract lambda.

import sys

sys.path.append("/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls")

import numpy as np
from sklearn.linear_model import LinearRegression
from typing import List, Tuple
from matplotlib import pyplot as plt
from lppls_defaults import SMALLEST_WINDOW_SIZE
from lppls_dataclasses import BubbleStart, BubbleType
from date_utils import DateUtils as du
from matplotlib import dates as mdates
from typechecking import TypeCheckBase


class Starts(TypeCheckBase):
    def getSSE(self, Y, Yhat, p=1, normed=False):
        """Obtain SSE (chi^2)
        p -> No. of parameters
        Y -> Data
        Yhat -> Model
        """
        error = sum([(Y[i] - Yhat[i]) ** 2 for i in range(len(Y))])
        obj = np.sum(error)
        if normed == False:
            obj = np.sum(error)
        else:
            obj = 1 / float(len(Y) - p) * np.sum(error)
        return obj

    def calculate_lambda_of_normed_cost(self, sse):
        # Create linear regression object using statsmodels package
        regr = LinearRegression(fit_intercept=False)

        # create x range for the sse_ds
        x_sse = np.arange(len(sse))
        x_sse = x_sse.reshape(len(sse), 1)

        # Train the model using the training sets
        res = regr.fit(x_sse, sse)

        return res.coef_[0]

    def getLagrangeScore(
        self, actual_prices: List[float], predicted_prices: List[float]
    ) -> Tuple[List[float], float]:
        ssrn_reg = []
        for i in range(len(actual_prices) - SMALLEST_WINDOW_SIZE):
            ssrn_reg.append(
                self.getSSE(actual_prices[i:-1], predicted_prices[i:-1], normed=True)
            )  # Classical SSE
        lambda_coeff = self.calculate_lambda_of_normed_cost(ssrn_reg)

        # Estimate the cost function pondered by lambda using a Shrinking Window.
        ssrn_lgrn = []
        for i in range(len(actual_prices) - SMALLEST_WINDOW_SIZE):
            ssrn_lgrn_term = ssrn_reg[i] - lambda_coeff * len(actual_prices[i:-1])  # SSE lagrange
            ssrn_lgrn.append(ssrn_lgrn_term)

        max_element = max(ssrn_lgrn)
        ssrn_lgrn = [x / max_element for x in ssrn_lgrn]

        return ssrn_lgrn, lambda_coeff

    def getSSE_and_SSEN_as_a_func_of_dt(
        self, actual_prices: List[float], predicted_prices: List[float]
    ):
        """Obtain SSE and SSE/N for a given shrinking fitting window"""

        # Get a piece of it: Shrinking Window
        _sse = []
        _ssen = []
        for i in range(len(actual_prices) - SMALLEST_WINDOW_SIZE):  # loop t1 until: t1 = t2 - 10:
            actual_prices_batch = actual_prices[i:-1]
            predicted_prices_batch = predicted_prices[i:-1]
            sse = self.getSSE(actual_prices_batch, predicted_prices_batch, normed=False)
            ssen = self.getSSE(actual_prices_batch, predicted_prices_batch, normed=True)
            _sse.append(sse)
            _ssen.append(ssen)

        return _sse / max(_sse), _ssen / max(_ssen), _ssen  # returns results + data

    def plot_all_fit_measures(self, actual_prices, predicted_prices, dates):
        bounded_sse, bounded_ssen, _ = self.getSSE_and_SSEN_as_a_func_of_dt(
            actual_prices, predicted_prices
        )
        ssen_reg, lambda_coeff = self.getLagrangeScore(actual_prices, predicted_prices)
        formated_dates = [du.ordinal_to_date(d) for d in dates]

        plt.figure(figsize=(10, 6))

        # Plot SSE, SSEN, SSEN Reg
        scores_len = len(bounded_sse)
        assert len(bounded_ssen) == scores_len and len(ssen_reg) == scores_len

        plt.plot(formated_dates[:scores_len], bounded_sse, color="green", label="SSE")
        plt.plot(
            formated_dates[:scores_len], bounded_ssen, color="blue", linestyle="--", label="SSEN"
        )
        plt.plot(
            formated_dates[:scores_len], ssen_reg, color="red", linestyle=":", label="SSEN Reg"
        )

        # Set labels, title, and legend for the fit measures plot
        plt.xlabel("Time")
        plt.ylabel("Values")
        plt.title("Fit Measures Over Time")
        ax = plt.gca()
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
        plt.legend()

        # Display lambda coefficient value
        lambda_label = r"$\lambda = {:}$".format(lambda_coeff)
        plt.text(
            0.05,
            0.95,
            lambda_label,
            transform=plt.gca().transAxes,
            fontsize=12,
            verticalalignment="top",
            bbox=dict(boxstyle="round", alpha=0.5),
        )

        # Create a completely separate plot for 'prices'
        plt.figure(figsize=(10, 6))
        plt.plot(formated_dates, actual_prices, color="purple", label="Prices")

        # Set labels and title for the prices plot

        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.title("Price Over Time")
        ax = plt.gca()
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
        plt.legend()

        plt.tight_layout()

    def compute_start_time(
        self,
        dates: List[int],
        actual_prices: List[float],
        predicted_prices: List[float],
        bubble_type: BubbleType,
        extremities,
    ) -> BubbleStart:
        # "We impose the constraint that, for a given developingbubble, its start time t1*
        # cannot be earlier than the previous peak, as determined in Figure 1.""
        #
        # Dissection of Bitcoin’s Multiscale Bubble History from January 2012 to February 2018
        last_extremity_index = 0
        if len(extremities) > 0:
            last_extremity_index = dates.index(extremities[-1].date_ordinal)
        ssrn_lgrn, _ = self.getLagrangeScore(
            actual_prices[last_extremity_index:], predicted_prices[last_extremity_index:]
        )

        min_index = last_extremity_index + ssrn_lgrn.index(min(ssrn_lgrn))
        return BubbleStart(dates[min_index], bubble_type)
