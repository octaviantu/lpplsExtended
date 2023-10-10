import numpy as np
import warnings
import logging

class LPPLSMath:

    @staticmethod
    def lppls(t: float, tc: float, m: float, w: float, a: float, b: float, c1: float, c2: float) -> float:
        assert t < tc, "we can only predict up to time t smaller than tc"
        return a + np.power(tc - t, m) * (b + ((c1 * np.cos(w * np.log(tc - t))) + (c2 * np.sin(w * np.log(tc - t)))))

    @staticmethod
    def matrix_equation(observations, tc, m, w):
        """
        Derive linear parameters in LPPLs from nonlinear ones.
        """
        assert observations[0][-1] < tc # all observations should be before tc
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

        matrix_1 = np.array([
            [N,          np.sum(fi),       np.sum(gi),       np.sum(hi)],
            [np.sum(fi), np.sum(fi_pow_2), np.sum(figi),     np.sum(fihi)],
            [np.sum(gi), np.sum(figi),     np.sum(gi_pow_2), np.sum(gihi)],
            [np.sum(hi), np.sum(fihi),     np.sum(gihi),     np.sum(hi_pow_2)]
        ])

        matrix_2 = np.array([
            [np.sum(yi)],
            [np.sum(yifi)],
            [np.sum(yigi)],
            [np.sum(yihi)]
        ])

        return np.linalg.solve(matrix_1, matrix_2)


    @staticmethod
    def sum_of_squared_residuals(x, observations):
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

        [price_prediction, actual_prices] = LPPLSMath.get_price_predictions(obs_up_to_tc, tc, m, w, a, b, c1, c2)
        delta = np.subtract(price_prediction, actual_prices)

        return np.sum(np.power(delta, 2))


    # TODO(octaviant) - find usage or delete
    @staticmethod
    def _is_O_in_range(tc: float, w: float, last: float, O_min: float) -> bool:
        return ((w / (2 * np.pi)) * np.log(abs(tc / (tc - last)))) > O_min

    # TODO(octaviant) - find usage or delete
    @staticmethod
    def _is_D_in_range(m: float, w: float, b: float, c: float, D_min: float) -> bool:
        return False if m <= 0 or w <= 0 else abs((m * b) / (w * c)) > D_min

    @staticmethod
    def get_oscillations(w: float, tc: float, t1: float, t2: float) -> float:
        assert t1 < tc, "we can only compute oscillations above the starting time"
        return ((w / 2.0) * np.log((tc - t1) / (t2 - t1)))

    @staticmethod
    def get_damping(m: float, w: float, b: float, c: float) -> float:
        return (m * np.abs(b)) / (w * np.abs(c))

    @staticmethod
    def get_c(c1: float, c2: float) -> float:
        if c1 and c2:
            # c = (c1 ** 2 + c2 ** 2) ** 0.5
            return c1 / np.cos(np.arctan(c2 / c1))
        else:
            return 0

    @staticmethod
    def get_price_predictions(observations, tc, m, w, a, b, c1, c2):
        price_prediction = []
        actual_prices = []
        
        for t, actual_price in zip(observations[0], observations[1]):
            assert t < tc, "we can only predict up to time t smaller than tc"
            predicted_price = LPPLSMath.lppls(t, tc, m, w, a, b, c1, c2)
            price_prediction.append(predicted_price)
            actual_prices.append(actual_price)

        return [price_prediction, actual_prices]

    @staticmethod
    def stop_observation_at_tc(observations, tc):
        first_larger_index = np.searchsorted(observations[0, :], tc, side='left') - 1
        return [observations[0, :first_larger_index], observations[1, :first_larger_index]]
