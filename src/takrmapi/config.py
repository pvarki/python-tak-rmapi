"""Configurations with .env support"""

from typing import Dict, Any, cast
from pathlib import Path
import json
import functools
import logging

from starlette.config import Config

LOGGER = logging.getLogger(__name__)


@functools.cache
def load_manifest(filepth: Path = Path("/pvarki/kraftwerk-init.json")) -> Dict[str, Any]:
    """Load the manifest"""
    if not filepth.exists():
        # return a dummy manifest
        LOGGER.warning("Returning dummy manifest")
        rm_uri = "https://localmaeher.dev.pvarki.fi"
        mtls_uri = rm_uri.replace("https://", "https://mtls.")
        return {
            "deployment": "localmaeher",
            "rasenmaeher": {
                "init": {"base_uri": rm_uri, "csr_jwt": "LOL, no"},
                "mtls": {"base_uri": mtls_uri},
                "certcn": "rasenmaeher",
            },
            "product": {"dns": "tak.localmaeher.dev.pvarki.fi"},
        }
    return cast(Dict[str, Any], json.loads(filepth.read_text(encoding="utf-8")))


def read_tak_fqdn() -> str:
    """Read the fqdn from manifest"""
    return str(load_manifest()["product"]["dns"])


def read_deployment_name() -> str:
    """Read the fqdn from manifest"""
    return str(load_manifest()["deployment"])


cfg = Config(
    env_prefix="TI"
)  # not supporting .env files anymore because https://github.com/encode/starlette/discussions/2446

LOG_LEVEL: int = cfg("LOG_LEVEL", default=10, cast=int)
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

# Used for mission pkgs
TAK_SERVER_FQDN: str = cfg("TAK_SERVER_FQDN", cast=str, default=read_tak_fqdn())
TAK_SERVER_NAME: str = cfg("TAK_SERVER_NAME", cast=str, default=read_deployment_name())
