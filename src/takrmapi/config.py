"""Configurations with .env support"""
from pathlib import Path

from starlette.config import Config

cfg = Config(".env")

LOG_LEVEL: int = cfg("LOG_LEVEL", default=20, cast=int)
TEMPLATES_PATH: Path = cfg("TEMPLATES_PATH", cast=Path, default=Path(__file__).parent / "templates")

TAK_CERTS_FOLDER: Path = cfg("TAK_CERTS_FOLDER", cast=Path, default=Path("/opt/tak/data/certs/files"))
RMAPI_PERSISTENT_FOLDER: Path = cfg("RMAPI_PERSISTENT_FOLDER", cast=Path, default=Path("/data/persistent"))
TAK_MISSIONPKG_TEMPLATES_FOLDER: Path = cfg(
    "TAK_MISSIONPKG_TEMPLATES_FOLDER", cast=Path, default=Path(__file__).parent / "templates" / "tak_missionpkg"
)
# There are some rumors for need of different mission packages, default lives under tak_missionpkg/default
TAK_MISSIONPKG_DEFAULT_MISSION: str = cfg("TAK_MISSIONPKG_DEFAULT_MISSION", cast=str, default="default")
TAK_MISSIONPKG_TMP: str = cfg(
    "TAK_MISSIONPKG_TMP", cast=str, default="/tmp"  # nosec B108 - TODO maybe in memory stuff to replace /tmp
)

TAK_MESSAGING_API_HOST: str = cfg("TAK_MESSAGING_API_HOST", cast=str, default="https://127.0.0.1")  # We are in sidecar
TAK_MESSAGING_API_PORT: int = cfg("TAK_MESSAGING_API_PORT", cast=int, default=8443)

TAKCL_CORECONFIG_PATH: Path = cfg("TAKCL_CORECONFIG_PATH", cast=Path, default=Path("/opt/tak/data/CoreConfig.xml"))
