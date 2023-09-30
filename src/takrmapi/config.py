"""Configurations with .env support"""
from pathlib import Path

from starlette.config import Config

cfg = Config(".env")

LOG_LEVEL: int = cfg("LOG_LEVEL", default=20, cast=int)
TEMPLATES_PATH: Path = cfg("TEMPLATES_PATH", cast=Path, default=Path(__file__).parent / "templates")
