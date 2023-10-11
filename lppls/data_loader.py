import pkg_resources
import pandas as pd
import json


def nasdaq_dotcom() -> pd.DataFrame:
    # This is a stream-like object. If you want the actual info, call
    # stream.read()
    stream = pkg_resources.resource_stream(__name__, "data/nasdaq_dotcom.csv")
    return pd.read_csv(stream, encoding="utf-8")


def load_config(filter_file):
    if filter_file:
        with open(filter_file, "r") as f:
            return json.load(f)
    return None  # Or set default values here
