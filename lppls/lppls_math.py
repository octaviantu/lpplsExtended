import numpy as np
from lppls.lppls_dataclasses import ObservationSeries, OptimizedParams
from typing import List
from common.typechecking import TypeCheckBase


class LPPLSMath(TypeCheckBase):
    @staticmethod
    def predict_log_price(t: float, op: OptimizedParams) -> float:
        tc, m, w, a, b, c1, c2 = op.tc, op.m, op.w, op.a, op.b, op.c1, op.c2

        assert t < tc, "we can only predict up to time t smaller than tc"
        return a + np.power(tc - t, m) * (
            b + ((c1 * np.cos(w * np.log(tc - t))) + (c2 * np.sin(w * np.log(tc - t))))
        )

    @staticmethod
    def matrix_equation(observations: ObservationSeries, tc, m, w) -> List[float]:
        """
        Derive linear parameters in LPPLs from nonlinear ones.
        """
        assert observations[-1].date_ordinal < tc  # all observations should be before tc
        D = observations.get_date_ordinals()
        logP = observations.get_log_prices()
        N = len(observations)

        dT = np.abs(tc - D)
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

        yi = logP
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
        return np.linalg.solve(matrix_1, matrix_2).flatten().tolist()


    @staticmethod
    def minimize_squared_residuals(x, observations: ObservationSeries):
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

        a, b, c1, c2 = LPPLSMath.matrix_equation(observations, tc, m, w)
        op = OptimizedParams(tc, m, w, a, b, c1, c2)

        return LPPLSMath.sum_of_squared_residuals(observations, op)

    @staticmethod
    def sum_of_squared_residuals(observations: ObservationSeries, op: OptimizedParams) -> float:
        log_price_predictions = LPPLSMath.get_log_price_predictions(observations, op)
        delta = np.subtract(log_price_predictions, observations.get_log_prices())

        return np.sum(np.power(delta, 2)) / len(delta)

    @staticmethod
    def get_c(c1: float, c2: float) -> float:
        if c1 and c2:
            # c = (c1 ** 2 + c2 ** 2) ** 0.5
            return c1 / np.cos(np.arctan(c2 / c1))
        else:
            return 0

    @staticmethod
    def get_log_price_predictions(
        observations: ObservationSeries, op: OptimizedParams
    ) -> List[float]:
        log_price_prediction = []
        date_ordinals = observations.get_date_ordinals()

        for t in date_ordinals:
            assert t < op.tc, "we can only predict up to time t smaller than tc"
            predicted_log_price = LPPLSMath.predict_log_price(t, op)
            log_price_prediction.append(predicted_log_price)

        return log_price_prediction
