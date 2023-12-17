import numpy as np
from sklearn.linear_model import LinearRegression
from typing import List, Tuple
from matplotlib import pyplot as plt
from lppls_defaults import SMALLEST_WINDOW_SIZE
from lppls_dataclasses import BubbleStart, BubbleType
from matplotlib import dates as mdates
from typechecking import TypeCheckBase
from filter_interface import FilterInterface
from lppls_dataclasses import ObservationSeries
from lppls_math import LPPLSMath
from data_fit import DataFit
from dataclasses import dataclass


@dataclass
class SquareErrors:
    squared_errors: List[float]

    def __len__(self):
        return len(self.squared_errors)

    def get_errors(self):
        return self.squared_errors

    def __getitem__(self, key):
        if isinstance(key, slice):
            # Handle slice objects
            return ObservationSeries(self.squared_errors[key])
        elif isinstance(key, int):
            # Handle integer index
            return self.squared_errors[key]
        else:
            raise TypeError("Invalid argument type.")

    def get_normalised_errors(self):
        max_element = max(self.squared_errors)
        return [x / max_element for x in self.squared_errors]



class Starts(TypeCheckBase):

    def calculate_lambda_of_normed_cost(self, ssen: SquareErrors) -> float:
        # Create linear regression object using statsmodels package
        regr = LinearRegression()
        x_ssen = [[i] for i in range(len(ssen))]

        # Train the model using the training sets
        res = regr.fit(x_ssen, ssen.get_errors())

        regression_line = res.predict(x_ssen)
        # Plotting the data and the regression line
        plt.figure(figsize=(10, 6))
        plt.scatter(x_ssen, ssen.get_errors(), color='blue', label='SSEN Data')
        plt.plot(x_ssen, regression_line, color='red', label='Regression Line')
        plt.xlabel('Index')
        plt.ylabel('SSEN Errors')
        plt.title('Linear Regression Without Intercept on SSEN Data')
        plt.legend()
        plt.grid(True)

        print('coef: ', res.coef_)
        return res.coef_[0]


    def get_lagrange_score(self, ssen: SquareErrors, interval_length: int) -> Tuple[SquareErrors, float]:
        lambda_coeff = self.calculate_lambda_of_normed_cost(ssen)

        # Estimate the cost function pondered by lambda using a Shrinking Window.
        ssen_lgrn = []
        for i in range(len(ssen)):
            window_len = interval_length - i
            ssen_lgrn_term = ssen[i] + lambda_coeff * window_len  # SSE lagrange
            ssen_lgrn.append(ssen_lgrn_term)

        return SquareErrors(ssen_lgrn), lambda_coeff


    def getSSE_and_SSEN_as_a_func_of_dt(self, observations: ObservationSeries, filter: FilterInterface) -> Tuple[SquareErrors, SquareErrors]:
        """Obtain SSE and SSE/N for a given shrinking fitting window"""

        # Get a piece of it: Shrinking Window
        _sse = []
        _ssen = []
        for i in range(len(observations) - SMALLEST_WINDOW_SIZE):  # loop t1 until: t1 = t2 - 10:
            current_obs = observations[i:-1]
            actual_prices = current_obs.get_prices()
            op = filter.fit(25, current_obs)

            data_fit = DataFit(current_obs, filter)
            if i > len(observations) - SMALLEST_WINDOW_SIZE - 10:
                data_fit.plot_fit(None, op)

            predicted_prices = list(np.exp(LPPLSMath.get_log_price_predictions(current_obs, op)))

            assert len(actual_prices) == len(predicted_prices)
            errors = [(actual_prices[i] - predicted_prices[i]) ** 2 for i in range(len(actual_prices))]
            sse = sum(errors)
            ssen = sse / float(len(actual_prices))

            _sse.append(sse)
            _ssen.append(ssen)

        print('SSE: ', _sse)
        print('SSEN: ', _ssen)
        return SquareErrors(_sse), SquareErrors(_ssen)  # returns results + data


    def plot_all_fit_measures(self, observations: ObservationSeries, filter: FilterInterface) -> None:
        sse, ssen = self.getSSE_and_SSEN_as_a_func_of_dt(observations, filter)

        ssen_lgrn, lambda_coeff = self.get_lagrange_score(ssen, len(observations))
        formated_dates = observations.get_formatted_dates()

        plt.figure(figsize=(10, 6))

        # Plot SSE, SSEN, SSEN Regi
        scores_len = len(sse)
        assert len(ssen) == scores_len and len(ssen_lgrn) == scores_len

        plt.plot(formated_dates[:scores_len], sse.get_normalised_errors(), color="green", label="SSE")
        plt.plot(
            formated_dates[:scores_len], ssen.get_normalised_errors(), color="blue", linestyle="--", label="SSEN"
        )
        plt.plot(
            formated_dates[:scores_len], ssen_lgrn.get_normalised_errors(), color="red", linestyle=":", label="SSEN Reg"
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

        # Create a completely separate plot for the absolute value of errors
        plt.figure(figsize=(10, 6))
        plt.plot(formated_dates[:scores_len], ssen.get_errors(), color="purple", label="Prices")
        plt.xlabel("Time")
        plt.ylabel("Errors")
        ax = plt.gca()
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))

    
        # Create a completely separate plot for 'prices'
        plt.figure(figsize=(10, 6))
        plt.plot(formated_dates, observations.get_prices(), color="purple", label="Prices")

        # Set labels and title for the prices plot
        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.title("Price Over Time")
        ax = plt.gca()
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
        plt.legend()

        plt.tight_layout()


    def compute_start_time_fixed(
        self,
        actual_prices: List[float],
        fiter: FilterInterface
    ) -> BubbleStart:
        # "We impose the constraint that, for a given developingbubble, its start time t1*
        # cannot be earlier than the previous peak, as determined in Figure 1.""
        #
        # Dissection of Bitcoin’s Multiscale Bubble History from January 2012 to February 2018

        ssen_lgrn, _ = self.get_lagrange_score(actual_prices, fiter)

        return ssen_lgrn.index(min(ssen_lgrn))    


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
        ssen_lgrn, _ = self.get_lagrange_score(
            actual_prices[last_extremity_index:], predicted_prices[last_extremity_index:]
        )

        min_index = last_extremity_index + ssen_lgrn.index(min(ssen_lgrn))
        return BubbleStart(dates[min_index], bubble_type)
