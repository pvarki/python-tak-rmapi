"""Helpers for reading typed values from environment variables"""

import os
import logging

LOGGER = logging.getLogger(__name__)


def env_float(key: str, default: float, min_value: float = 0.0, max_value: float = float("inf")) -> float:
    """Read a float from an environment variable with exclusive bounds (min_value, max_value).

    Values that are out of range, non-numeric, or infinite fall back to the default.
    """
    try:
        value = float(os.getenv(key) or default)
        if not min_value < value < max_value:
            raise ValueError(f"{value} out of range ({min_value}, {max_value})")
        return value
    except (TypeError, ValueError):
        LOGGER.warning("Invalid value for %s, using default %s", key, default)
        return default
