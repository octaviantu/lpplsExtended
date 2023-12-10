from datetime import date
import pandas as pd
from datetime import datetime, timedelta
from typechecking import TypeCheckBase


class DateUtils(TypeCheckBase):
    @staticmethod
    def ordinal_to_date(ordinal: int) -> str:
        # Since pandas represents timestamps in nanosecond resolution,
        # the time span that can be represented using a 64-bit integer
        # is limited to approximately 584 years
        return date.fromordinal(ordinal).strftime("%Y-%m-%d")

    @staticmethod
    def date_to_ordinal(date: date) -> int:
        return pd.Timestamp(date).toordinal()

    @staticmethod
    def today() -> str:
        return datetime.today().strftime("%Y-%m-%d")

    @staticmethod
    def days_ago(number_of_days: int) -> str:
        return (datetime.now() - timedelta(days=number_of_days)).strftime("%Y-%m-%d")

    @staticmethod
    def day_of_week(day: str) -> str:
        date_obj = datetime.strptime(day, "%Y-%m-%d").date()  # Parse the string to a date object
        return date_obj.strftime("%A")  # Returns the full name of the weekday
