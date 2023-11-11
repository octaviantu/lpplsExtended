import sys
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls"
)

import numpy as np
from sklearn.linear_model import LinearRegression
from lppls_defaults import SMALLEST_WINDOW_SIZE
from typing import List, Tuple
from matplotlib import pyplot as plt
from numpy.typing import NDArray

class Starts:
    def getSSE(self, Y, Yhat, p=1, normed=False):
        """ Obtain SSE (chi^2)
        p -> No. of parameters
        Y -> Data
        Yhat -> Model
        """
        error = sum([(Y[i]-Yhat[i])**2 for i in range(len(Y))])
        obj = np.sum(error)
        if normed == False:
            obj = np.sum(error)
        else:
            obj = 1/float(len(Y) - p) * np.sum(error)
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


    def getLagrangeScore(self, actualP: List[float], predictedP: List[float]) -> Tuple[List[float], float]:

        ssrn_reg = []
        for i in range(len(actualP) - SMALLEST_WINDOW_SIZE):
            ssrn_reg.append(self.getSSE(actualP[i:-1], predictedP[i:-1], normed=True)) # Classical SSE
        lambda_coeff = self.calculate_lambda_of_normed_cost(ssrn_reg)

        # Estimate the cost function pondered by lambda using a Shrinking Window.
        ssrn_lgrn = []
        for i in range(len(actualP) - SMALLEST_WINDOW_SIZE):
            ssrn_lgrn_term = ssrn_reg[i] - lambda_coeff*len(actualP[i:-1]) # SSE lagrange
            ssrn_lgrn.append(ssrn_lgrn_term)

        max_element = max(ssrn_lgrn)
        ssrn_lgrn = [x / max_element for x in ssrn_lgrn]

        return ssrn_lgrn, lambda_coeff


    def fitDataViaOlsGetBetaAndLine(self, X: NDArray, Y: NDArray) -> NDArray:
        """ Fit synthetic OLS """
        # Assuming X is a vector and needs to be a matrix with an intercept term
        X_matrix = np.vstack((np.ones(len(X)), X)).T  # Add a column of ones for the intercept
        # Calculate beta_hat using the OLS formula (X'X)^-1X'Y
        beta_hat = np.dot(np.linalg.inv(np.dot(X_matrix.T, X_matrix)), np.dot(X_matrix.T, Y))
        # Calculate predicted Y values
        Y_hat = np.dot(X_matrix, beta_hat)
        return Y_hat


    def getSSE_and_SSEN_as_a_func_of_dt(self, X: List[float], Y: List[float]):
        """ Obtain SSE and SSE/N for a given shrinking fitting window """

        # Get a piece of it: Shrinking Window
        _sse = []
        _ssen = []
        for i in range(len(X)-10):  # loop t1 until: t1 = t2 - 10:
            xBatch = X[i:-1]
            yBatch = Y[i:-1]
            YhatBatch = self.fitDataViaOlsGetBetaAndLine(xBatch, yBatch)
            sse = self.getSSE(yBatch, YhatBatch, normed=False)
            ssen = self.getSSE(yBatch, YhatBatch, normed=True)
            _sse.append(sse)
            _ssen.append(ssen)

        return _sse/max(_sse), _ssen/max(_ssen), _ssen  # returns results + data


    def plot_all_fit_measures(self, X, Y):

        bounded_sse, bounded_ssen, _ = self.getSSE_and_SSEN_as_a_func_of_dt(X, Y)
        Yhat = self.fitDataViaOlsGetBetaAndLine(X,Y) # Get Model fit
        ssen_reg, lambda_coeff = self.getLagrangeScore(Y, Yhat)

        plt.figure(figsize=(10, 6))

        # Plot SSE, SSEN, SSEN Reg
        plt.plot(bounded_sse, color='green', label='SSE')
        plt.plot(bounded_ssen, color='blue', linestyle='--', label='SSEN')
        plt.plot(ssen_reg, color='red', linestyle=':', label='SSEN Reg')

        # Set labels, title, and legend for the fit measures plot
        plt.xlabel('Time')
        plt.ylabel('Values')
        plt.title('Fit Measures Over Time')
        plt.legend()

        # Display lambda coefficient value
        lambda_label = r'$\lambda = {:}$'.format(lambda_coeff)
        plt.text(0.05, 0.95, lambda_label, transform=plt.gca().transAxes, fontsize=12,
                verticalalignment='top', bbox=dict(boxstyle="round", alpha=0.5))


        # Create a completely separate plot for 'prices'
        plt.figure(figsize=(10, 6))
        plt.plot(Y, color='purple', label='Prices')

        # Set labels and title for the prices plot
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.title('Price Over Time')
        plt.legend()

        plt.tight_layout()
        plt.show()
