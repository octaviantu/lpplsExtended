from typing import List, Dict, Tuple
from scipy.optimize import minimize
from lppls_math import LPPLSMath
import numpy as np
import random
import data_loader
from lppls_defaults import MAX_SEARCHES, SMALLEST_WINDOW_SIZE
from math import floor, ceil
import matplotlib.pyplot as plt

class FilimonovPlot():
    def __init__(self, filter_file="./lppls/conf/filimonov_filter.json"):
        self.filter_criteria = data_loader.load_config(filter_file)


    def plot_optimum(self, obs: np.ndarray, minimizer: str = "Nelder-Mead") -> None:
        t1, t2 = obs[0, 0], obs[0, -1]
        tc_lower = self.filter_criteria.get("tc_lower")
        tc_upper = self.filter_criteria.get("tc_upper")

        dates, ms, ws, ssrs = [], [], [], []
        for t in range(floor(t1) + SMALLEST_WINDOW_SIZE, ceil(t2) - SMALLEST_WINDOW_SIZE):
            for tc in range(t + tc_lower, t + tc_upper):
                obs_up_to_tc = LPPLSMath.stop_observation_at_tc(obs, tc)

                search_count = 0
                min_ssr = np.inf
                best_m, best_w = np.inf, np.inf
                # find bubble
                while search_count < MAX_SEARCHES:
                    tc_lower = self.filter_criteria.get("tc_lower")
                    tc_upper = self.filter_criteria.get("tc_upper")

                    m_bounds = (self.filter_criteria.get("m_min"), self.filter_criteria.get("m_max"))
                    w_bounds = (self.filter_criteria.get("w_min"), self.filter_criteria.get("w_max"))
                    search_bounds = [m_bounds, w_bounds]

                    m = random.uniform(*m_bounds)
                    w = random.uniform(*w_bounds)

                    seed = np.array([m, w])

                    success, params_dict = self.estimate_params(obs_up_to_tc, seed, minimizer, search_bounds, tc)

                    if success:
                        m, w, a, b, _, c1, c2 = params_dict.values()
                        ssr = LPPLSMath.sum_of_squared_residuals(obs_up_to_tc, tc, m, w, a, b, c1, c2)
                        if ssr < min_ssr:
                            min_ssr = ssr
                            best_m = m
                            best_w = w

                        break
                    else:
                        search_count += 1

                dates.append(LPPLSMath.ordinal_to_date(t))
                ms.append(best_m)
                ws.append(best_w)
                ssrs.append(min_ssr)

        plt.figure(figsize=(10, 6))

        # Plotting ssr
        ax1 = plt.subplot(3, 1, 1)
        plt.plot(dates, ssrs, 'k-', label='F2(tc)')
        plt.ylabel('F2(tc)')
        plt.title('Dependence of the cost function and estimated parameters')
        self.set_four_x_ticks(ax1, dates)

        # Plotting m
        ax2 = plt.subplot(3, 1, 2)
        plt.plot(dates, ms, 'k-', label='m(tc)')
        plt.ylabel('m(tc)')
        self.set_four_x_ticks(ax2, dates)

        # Plotting w
        ax3 = plt.subplot(3, 1, 3)
        plt.plot(dates, ws, 'k-', label='w(tc)')
        plt.ylabel('w(tc)')
        plt.xlabel('tc')
        self.set_four_x_ticks(ax3, dates)

        plt.tight_layout()
        plt.show()


    def set_four_x_ticks(self, ax, tc_dates):
        ax.set_xticks(tc_dates[::len(tc_dates)//3])  # 3 intervals -> 4 ticks
        ax.set_xticklabels([date for date in tc_dates[::len(tc_dates)//3]])


    def estimate_params(
        self,
        obs_up_to_tc: List[List[float]],
        seed: np.ndarray,
        minimizer: str,
        search_bounds: List[Tuple[float, float]],
        tc: float
    ) -> Tuple[bool, Dict[str, float]]:
        """
        Args:
            obs_up_to_tc (list):  the observed time-series data.
            seed (list):  time-critical, omega, and m.
            minimizer (str):  See list of valid methods to pass to scipy.optimize.minimize:
                https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html#scipy.optimize.minimize
        Returns:
            A tuple with a boolean indicating success, and a dictionary with the values of tc, m, w, a, b, c, c1, c2.
        """

        cofs = minimize(
            args=(obs_up_to_tc, tc),
            fun=FilimonovPlot.minimize_squared_residuals_with_fixed_tc,
            x0=seed,
            method=minimizer,
            bounds=search_bounds,
        )

        if cofs.success:
            m = cofs.x[0]
            w = cofs.x[1]

            rM = LPPLSMath.matrix_equation(obs_up_to_tc, tc, m, w)
            a, b, c1, c2 = rM[:, 0].tolist()

            c = LPPLSMath.get_c(c1, c2)

            params_dict = {"m": m, "w": w, "a": a, "b": b, "c": c, "c1": c1, "c2": c2}
            return True, params_dict
        else:
            return False, {}


    @staticmethod
    def minimize_squared_residuals_with_fixed_tc(x, obs_up_to_tc, tc):
        
        m = x[0]
        w = x[1]

        rM = LPPLSMath.matrix_equation(obs_up_to_tc, tc, m, w)
        a, b, c1, c2 = rM[:, 0].tolist()

        return LPPLSMath.sum_of_squared_residuals(obs_up_to_tc, tc, m, w, a, b, c1, c2)
