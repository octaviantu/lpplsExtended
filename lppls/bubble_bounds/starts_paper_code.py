# Python script for computing the Lambda regulariser metric - OLS case.
# Copyright: G. Demos @ ETH-Zurich - Jan.2017

# Copied but heavily refactored from https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3007070


import numpy as np
from sklearn.linear_model import LinearRegression
from matplotlib import pyplot as plt
from numpy.typing import NDArray


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


def fitDataViaOlsGetBetaAndLine(X: NDArray, Y: NDArray) -> NDArray:
    """ Fit synthetic OLS """
    # Assuming X is a vector and needs to be a matrix with an intercept term
    X_matrix = np.vstack((np.ones(len(X)), X)).T  # Add a column of ones for the intercept
    # Calculate beta_hat using the OLS formula (X'X)^-1X'Y
    beta_hat = np.dot(np.linalg.inv(np.dot(X_matrix.T, X_matrix)), np.dot(X_matrix.T, Y))
    # Calculate predicted Y values
    Y_hat = np.dot(X_matrix, beta_hat)
    return Y_hat


def getSSE(Y, Yhat, p=1, normed=False):
    """ Obtain SSE (chi^2)
    p -> No. of parameters
    Y -> Data
    Yhat -> Model
    """
    error = (Y-Yhat)**2.
    obj = np.sum(error)
    if normed == False:
        obj = np.sum(error)
    else:
        obj = 1/float(len(Y) - p) * np.sum(error)
    return obj


def getSSE_and_SSEN_as_a_func_of_dt():
    """ Obtain SSE and SSE/N for a given shrinking fitting window """
    # Simulate Initial Data
    X, Y = simulateOLS()

    # Get a piece of it: Shrinking Window
    _sse = []
    _ssen = []
    for i in range(len(X)-10):  # loop t1 until: t1 = t2 - 10:
        xBatch = X[i:-1]
        yBatch = Y[i:-1]
        YhatBatch = fitDataViaOlsGetBetaAndLine(xBatch, yBatch)
        sse = getSSE(yBatch, YhatBatch, normed=False)
        ssen = getSSE(yBatch, YhatBatch, normed=True)
        _sse.append(sse)
        _ssen.append(ssen)

    return _sse/max(_sse), _ssen/max(_ssen), _ssen, X, Y  # returns results + data


def calculate_lambda_of_normed_cost(sse):
    # Create linear regression object using statsmodels package
    regr = LinearRegression(fit_intercept=False)

    # create x range for the sse_ds
    x_sse = np.arange(len(sse))
    x_sse = x_sse.reshape(len(sse), 1)

    # Train the model using the training sets
    res = regr.fit(x_sse, sse)

    return res.coef_[0]


def obtainLagrangeRegularizedNormedCost(X, Y, lambda_coeff):
    """ Obtain the Lagrange regulariser for a given SSE/N Pt. """
    Yhat = fitDataViaOlsGetBetaAndLine(X,Y) # Get Model fit
    ssrn_reg = getSSE(Y, Yhat, normed=True) # Classical SSE
    ssrn_lgrn = ssrn_reg - lambda_coeff*len(Y) # SSE lagrange
    return ssrn_lgrn


def getSSEandRegVectorForLagrangeMethod(X, Y, lambda_coeff, bounded=False):
    """
    X and Y used for calculating the original SSEN
    lambda_coeff is the beta of fitting OLS to the SSEN
    """
    # Estimate the cost function pondered by lambda using a Shrinking Window.
    _ssenReg = []
    for i in range(len(X)-10):
        xBatch = X[i:-1]
        yBatch = Y[i:-1]
        regLag = obtainLagrangeRegularizedNormedCost(xBatch, yBatch, lambda_coeff)
        _ssenReg.append(regLag)

    if bounded:
        return _ssenReg/max(_ssenReg)
    else:
        return _ssenReg


def plot_all_fit_measures():
    bounded_sse, bounded_ssen, ssen, X, Y = getSSE_and_SSEN_as_a_func_of_dt()
    lambda_coeff = calculate_lambda_of_normed_cost(ssen)
    ssen_reg = getSSEandRegVectorForLagrangeMethod(X, Y, lambda_coeff, bounded=True)

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


if __name__ == "__main__":
    plot_all_fit_measures()
