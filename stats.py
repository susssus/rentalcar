"""
Stats from price history: average, median, percentile. Used to define "cheap".
"""
import math
import logging
from storage import get_price_per_day_history

logger = logging.getLogger(__name__)


def median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def percentile(values: list[float], p: float) -> float | None:
    """p in [0, 1]. E.g. 0.25 = 25th percentile."""
    if not values or p < 0 or p > 1:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[int(f)] * (c - k) + s[int(c)] * (k - f)


def get_stats(pickup_date: str | None = None, dropoff_date: str | None = None) -> dict:
    """
    Returns dict: avg_per_day, median_per_day, p25_per_day, count, is_cheap_threshold (p25).
    """
    history = get_price_per_day_history(pickup_date, dropoff_date)
    count = len(history)
    avg = average(history)
    med = median(history)
    p25 = percentile(history, 0.25)

    return {
        "avg_per_day": avg,
        "median_per_day": med,
        "p25_per_day": p25,
        "count": count,
        "cheap_threshold_p25": p25,
    }


def is_cheap(current_price_per_day: float, cheap_percentile: float = 0.25,
             pickup_date: str | None = None, dropoff_date: str | None = None) -> tuple[bool, float | None]:
    """
    True if current_price_per_day is at or below the given percentile of history.
    Returns (is_cheap, threshold_used).
    """
    history = get_price_per_day_history(pickup_date, dropoff_date)
    if len(history) < 3:
        # Not enough data: consider it cheap if we have any price (so we keep recording)
        return (True, None)
    th = percentile(history, cheap_percentile)
    if th is None:
        return (False, None)
    return (current_price_per_day <= th, th)
