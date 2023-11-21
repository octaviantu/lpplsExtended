import yfinance as yf
import logging

def calculate_value_score(ticker):

    # Set the logging level to debug
    logging.basicConfig(level=logging.DEBUG)

    # Get stock info
    stock = yf.Ticker(ticker)
    print(f'stock.info: {stock.info}')
    
    # Get financials
    income_statement = stock.financials
    balance_sheet = stock.balance_sheet
    cash_flow = stock.cash_flow
    market_cap = stock.info['marketCap']

    # Calculate Net Income (from the income statement)
    net_income = income_statement.loc['Net Income']

    # Calculate Invested Capital (equity + debt)
    total_debt = balance_sheet.loc['Total Debt']
    total_equity = balance_sheet.loc['Total Stockholder Equity']
    invested_capital = total_debt + total_equity

    # ROIC = Net Income / Invested Capital
    roic = net_income / invested_capital

    # EV = Market Cap + Total Debt - Cash
    cash = balance_sheet.loc['Cash']
    enterprise_value = market_cap + total_debt - cash

    # EV/IC
    ev_ic = enterprise_value / invested_capital

    # Value Score (this would depend on how you define 'comparing' ROIC and EV/IC)
    value_score = roic / ev_ic  # Example of a simple comparison

    return value_score

# Example usage
ticker = 'AAPL'  # Replace with your desired ticker
value_score = calculate_value_score(ticker)
print(f"The value score for {ticker} is: {value_score}")
