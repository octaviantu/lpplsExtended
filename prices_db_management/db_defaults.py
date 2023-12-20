import os

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = "asset_prices"
DB_USER = "sornette"
DB_PASSWORD = "sornette"


# For simulating the results, this will be default sum invested.
DEFAULT_POSITION_SIZE = 10000

# In practice the confidence that an asset is in a bubble rarely goes over 0.4
# But of course, the maximum is 1.
TOP_BUBBLE_CONFIDENCE_IN_PRACTICE = 0.4
