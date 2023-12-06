

# I don't want to trade leveraged ETFs - they decline in value because of their structure
BANNED_KEYWORDS = ["Bear ", "Bull ", "Leveraged ", "3X ", "2X ", "1.5X "]

BANNED_TICKERS = [
    # MMF - fluctuations irrelevant
    "SGOV",
    "USFR",
    "BIL",
    "SHV",
    # Short term treasury - fluctuations noisy
    "SHY",
    "VGSH",
    # Leveraged QQQ
    "PSQ"
    # The price is too low (close to 1), making my log formulas not work
    "GSAT"
]

def is_banned(ticker: str, security_name: str) -> bool:
    # In case the security is an ETF, reject some types of etfs.
    return any(keyword in security_name for keyword in BANNED_KEYWORDS) or ticker in BANNED_TICKERS
