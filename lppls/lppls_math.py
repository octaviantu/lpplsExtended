import numpy as np
from typing import List
from datetime import datetime as date
from pandas._libs.tslibs.np_datetime import OutOfBoundsDatetime
import pandas as pd


class LPPLSMath:
    @staticmethod
    def lppls(
        t: float, tc: float, m: float, w: float, a: float, b: float, c1: float, c2: float
    ) -> float:
        assert t < tc, "we can only predict up to time t smaller than tc"
        return a + np.power(tc - t, m) * (
            b + ((c1 * np.cos(w * np.log(tc - t))) + (c2 * np.sin(w * np.log(tc - t))))
        )

    @staticmethod
    def matrix_equation(observations, tc, m, w):
        """
        Derive linear parameters in LPPLs from nonlinear ones.
        """
        assert observations[0][-1] < tc  # all observations should be before tc
        T = observations[0]
        P = observations[1]
        N = len(T)

        dT = np.abs(tc - T)
        phase = np.log(dT)

        fi = np.power(dT, m)
        gi = fi * np.cos(w * phase)
        hi = fi * np.sin(w * phase)

        fi_pow_2 = np.power(fi, 2)
        gi_pow_2 = np.power(gi, 2)
        hi_pow_2 = np.power(hi, 2)

        figi = np.multiply(fi, gi)
        fihi = np.multiply(fi, hi)
        gihi = np.multiply(gi, hi)

        yi = P
        yifi = np.multiply(yi, fi)
        yigi = np.multiply(yi, gi)
        yihi = np.multiply(yi, hi)

        matrix_1 = np.array(
            [
                [N, np.sum(fi), np.sum(gi), np.sum(hi)],
                [np.sum(fi), np.sum(fi_pow_2), np.sum(figi), np.sum(fihi)],
                [np.sum(gi), np.sum(figi), np.sum(gi_pow_2), np.sum(gihi)],
                [np.sum(hi), np.sum(fihi), np.sum(gihi), np.sum(hi_pow_2)],
            ]
        )

        matrix_2 = np.array([[np.sum(yi)], [np.sum(yifi)], [np.sum(yigi)], [np.sum(yihi)]])

        return np.linalg.solve(matrix_1, matrix_2)

    @staticmethod
    def minimize_squared_residuals(x, observations):
        """
        Finds the least square difference.
        See https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html
        Args:
            x(np.ndarray):  1-D array with shape (n,).
            args:           Tuple of the fixed parameters needed to completely specify the function.
        Returns:
            (float)
        """

        tc = x[0]
        m = x[1]
        w = x[2]
        obs_up_to_tc = LPPLSMath.stop_observation_at_tc(observations, tc)

        rM = LPPLSMath.matrix_equation(obs_up_to_tc, tc, m, w)
        a, b, c1, c2 = rM[:, 0].tolist()

        return LPPLSMath.sum_of_squared_residuals(obs_up_to_tc, tc, m, w, a, b, c1, c2)

    @staticmethod
    def sum_of_squared_residuals(
        obs_up_to_tc: List[List[float]],
        tc: float,
        m: float,
        w: float,
        a: float,
        b: float,
        c1: float,
        c2: float,
    ) -> float:
        [price_prediction, actual_prices] = LPPLSMath.get_log_price_predictions(
            obs_up_to_tc, tc, m, w, a, b, c1, c2
        )
        delta = np.subtract(price_prediction, actual_prices)

        return np.sum(np.power(delta, 2)) / len(delta)


    @staticmethod
    def get_c(c1: float, c2: float) -> float:
        if c1 and c2:
            # c = (c1 ** 2 + c2 ** 2) ** 0.5
            return c1 / np.cos(np.arctan(c2 / c1))
        else:
            return 0

    @staticmethod
    def get_log_price_predictions(observations, tc, m, w, a, b, c1, c2):
        price_prediction = []
        actual_prices = []

        for t, actual_price in zip(observations[0], observations[1]):
            assert t < tc, "we can only predict up to time t smaller than tc"
            predicted_price = LPPLSMath.lppls(t, tc, m, w, a, b, c1, c2)
            price_prediction.append(predicted_price)
            actual_prices.append(actual_price)

        return [price_prediction, actual_prices]

    @staticmethod
    def stop_observation_at_tc(observations: List[List[float]], tc: float) -> List[List[float]]:
        first_larger_index = np.searchsorted(observations[0], tc, side="left") - 1
        return [observations[0][:first_larger_index], observations[1][:first_larger_index]]

    @staticmethod
    def ordinal_to_date(ordinal: int) -> str:
        # Since pandas represents timestamps in nanosecond resolution,
        # the time span that can be represented using a 64-bit integer
        # is limited to approximately 584 years
        try:
            return date.fromordinal(int(ordinal)).strftime("%Y-%m-%d")
        except (ValueError, OutOfBoundsDatetime):
            return str(pd.NaT)
