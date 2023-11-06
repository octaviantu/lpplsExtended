# Python script for computing the Lambda regulariser metric - OLS case.
# Copyright: G. Demos @ ETH-Zurich - Jan.2017

import numpy as np
from sklearn import linear_model
from matplotlib import pyplot as plt

def simulateOLS():
    """ Generate synthetic OLS as presented in the paper """
    nobs = 200
    X = np.arange(0, nobs, 1)
    e = np.random.normal(0, 10, nobs)
    beta = 0.5
    Y = [beta*X[i] + e[i] for i in range(len(X))]
    Y = np.array(Y)
    X = np.array(X)
    Y[0:100] = Y[0:100] + 4*e[0:100]
    Y[100:200] = Y[100:200]*8
    return X, Y


def fitDataViaOlsGetBetaAndLine(X,Y):
    """ Fit synthetic OLS """
    beta_hat = np.dot(np.dot(X.T,X)**-1. * np.dot(X.T,Y))
    Y = [beta_hat*X[i] for i in range(len(X))]  # generate fit
    return Y


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
        obj = 1/np.float(len(Y) - p) * np.sum(error)
    return obj


def getSSE_and_SSEN_as_a_func_of_dt(normed=False, plot=False):
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

    if plot == False:
        pass
    else:
        f, ax = plt.subplots(1,1,figsize=(6,3))
        ax.plot(_sse, color='k')
        a = ax.twinx()
        a.plot(_ssen, color='b')
        plt.tight_layout()

    if normed==False:
        return _sse, _ssen, X, Y  # returns results + data
    else:
        return _sse/max(_sse), _ssen/max(_ssen), X, Y  # returns results + data


def LagrangeMethod(sse):
    """ Obtain the Lagrange regulariser for a given SSE/N"""
    # Fit the decreasing trend of the cost function
    slope = calculate_slope_of_normed_cost(sse)
    return slope[0]


def calculate_slope_of_normed_cost(sse):
    # Create linear regression object using statsmodels package
    regr = linear_model.LinearRegression(fit_intercept=False)

    # create x range for the sse_ds
    x_sse = np.arange(len(sse))
    x_sse = x_sse.reshape(len(sse), 1)

    # Train the model using the training sets
    res = regr.fit(x_sse, sse)

    return res.coef_


def obtainLagrangeRegularizedNormedCost(X, Y, slope):
    """ Obtain the Lagrange regulariser for a given SSE/N Pt. """
    Yhat = fitDataViaOlsGetBetaAndLine(X,Y) # Get Model fit
    ssrn_reg = getSSE(Y, Yhat, normed=True) # Classical SSE
    ssrn_lgrn = ssrn_reg - slope*len(Y) # SSE lagrange

    return ssrn_lgrn


def getSSEandRegVectorForLagrangeMethod(X, Y, slope):
    """
    X and Y used for calculating the original SSEN
    slope is the beta of fitting OLS to the SSEN
    """
    # Estimate the cost function pondered by lambda using a Shrinking Window.
    _ssenReg = []
    for i in range(len(X)-10):
        xBatch = X[i:-1]
        yBatch = Y[i:-1]
        regLag = obtainLagrangeRegularizedNormedCost(xBatch, yBatch, slope)
        _ssenReg.append(regLag)
    
    return _ssenReg
