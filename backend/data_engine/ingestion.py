import logging
import os
from functools import wraps

import fastf1
import polars as pl
import psutil

from backend.core import config

logger = logging.getLogger(__name__)

CACHE_DIR = config.CACHE_DIR
fastf1.Cache.enable_cache(str(CACHE_DIR))


class MemoryLimitExceeded(Exception):
    pass


def check_memory_limit(limit_gb: float = 12.0, min_available_gb: float = 0.5):
    """Aborts before a heavy operation when RAM is nearly exhausted, and warns
    when the configured working-set budget is exceeded afterwards."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            available_gb = psutil.virtual_memory().available / (1024 ** 3)
            if available_gb < min_available_gb:
                raise MemoryLimitExceeded(
                    f"Only {available_gb:.2f} GB RAM available; refusing to run {func.__name__}."
                )

            result = func(*args, **kwargs)

            used_gb = psutil.Process(os.getpid()).memory_info().rss / (1024 ** 3)
            if used_gb > limit_gb:
                logger.warning(
                    "Process memory after %s is %.2f GB (budget %.1f GB).",
                    func.__name__, used_gb, limit_gb,
                )
            return result

        return wrapper

    return decorator


class FastF1Processor:
    @staticmethod
    @check_memory_limit(limit_gb=12.0)
    def fetch_and_stream_session(year: int, event: str, session_type: str):
        """Ingests FIA data using FastF1 and converts laps/weather to Polars."""
        logger.info("Fetching session: %s %s %s", year, event, session_type)

        session = fastf1.get_session(year, event, session_type)
        session.load(telemetry=True, laps=True, weather=True, messages=False)

        laps_pl = pl.from_pandas(session.laps)
        weather_pl = pl.from_pandas(session.weather_data) if session.weather_data is not None else None

        logger.info("Session %s %s %s loaded successfully.", year, event, session_type)

        return {
            "session": session,
            "laps_pl": laps_pl,
            "weather_pl": weather_pl,
        }
