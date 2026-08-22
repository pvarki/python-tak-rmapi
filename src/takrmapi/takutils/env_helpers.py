"""Helpers for reading typed values from environment variables"""

import os
import logging
import functools

from ..config import TAKCL_CORECONFIG_PATH

LOGGER = logging.getLogger(__name__)


def env_float(key: str, default: float, min_value: float = 0.0, max_value: float = 600.0) -> float:
    """Read a float from an environment variable with inclusive bounds [min_value, max_value].

    Raises ValueError immediately if default is outside the allowed range, as that is a
    programming error. Invalid or out-of-range env var values fall back to the default.
    """
    if not min_value <= default <= max_value:
        raise ValueError(f"default {default} is outside allowed range [{min_value}, {max_value}]")
    try:
        value = float(os.getenv(key) or default)
        if not min_value <= value <= max_value:
            raise ValueError(f"{value} out of range [{min_value}, {max_value}]")
        return value
    except (TypeError, ValueError):
        LOGGER.warning("Invalid value for %s, using default %s", key, default)
        return default


@functools.cache
def tak_version() -> tuple[int, int, int]:
    """Read /opt/tak/version.txt and return the parts"""
    fpath = TAKCL_CORECONFIG_PATH.parent.parent / "version.txt"
    if not fpath.exists():
        LOGGER.error("{} does not exist".format(fpath))
        return -1, -1, -1
    version_str = fpath.read_text(encoding="utf-8")
    mainver, release = version_str.split("-RELEASE-")
    parts = mainver.split(".")
    return int(parts[0]), int(parts[1]), int(release)
