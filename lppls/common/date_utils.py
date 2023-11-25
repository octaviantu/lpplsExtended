from datetime import date

def ordinal_to_date(ordinal: int) -> str:
    # Since pandas represents timestamps in nanosecond resolution,
    # the time span that can be represented using a 64-bit integer
    # is limited to approximately 584 years
    return date.fromordinal(ordinal).strftime("%Y-%m-%d")
