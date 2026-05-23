"""Configurations with .env support"""

from typing import Dict, Any, cast
from pathlib import Path
import json
import functools
import logging
import os

from starlette.config import Config

LOGGER = logging.getLogger(__name__)


@functools.cache
def load_manifest(filepth: Path = Path("/pvarki/kraftwerk-init.json")) -> Dict[str, Any]:
    """Load the manifest"""
    if not filepth.exists():
        altfile = Path("/pvarki/kraftwerk-rasenmaeher-init.json")
        if altfile.exists():
            filepth = altfile
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


def read_product_certcn() -> str:
    """Read the product certificate CN from manifest."""
    manifest = load_manifest()
    product = cast(Dict[str, Any], manifest.get("product", {}))
    if "certcn" in product:
        return str(product["certcn"])
    products = cast(Dict[str, Any], manifest.get("products", {}))
    if "tak" in products and "certcn" in products["tak"]:
        return str(products["tak"]["certcn"])
    return read_tak_fqdn()


def read_deployment_name() -> str:
    """Read the fqdn from manifest"""
    return str(load_manifest()["deployment"])


def read_rm_mtls_base_uri() -> str:
    """Read the RM mTLS API base URI from manifest."""
    return str(load_manifest()["rasenmaeher"]["mtls"]["base_uri"])


def read_product_api_base(product_name: str) -> str:
    """Read product API base URI from manifest, with a local fallback."""
    manifest = load_manifest()
    products = cast(Dict[str, Any], manifest.get("products", {}))
    if product_name in products and "api" in products[product_name]:
        return str(products[product_name]["api"])
    product_https_port = int(os.getenv("TI_PRODUCT_HTTPS_PORT", "4626"))
    return f"https://{product_name}.{read_deployment_name()}.dev.pvarki.fi:{product_https_port}"


def default_rm_product_cert_path() -> Path:
    """Resolve the RM product client certificate path."""
    candidates = [
        RMAPI_PERSISTENT_FOLDER / "public" / f"{read_product_certcn()}.pem",
        RMAPI_PERSISTENT_FOLDER / "public" / "mtlsclient.pem",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def default_rm_product_key_path() -> Path:
    """Resolve the RM product client private key path."""
    candidates = [
        RMAPI_PERSISTENT_FOLDER / "private" / f"{read_product_certcn()}.key",
        RMAPI_PERSISTENT_FOLDER / "private" / "mtlsclient.key",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def resolve_rm_product_path(configured: Path, fallback: Path) -> Path:
    """Use configured path when present, otherwise fall back to discovered path."""
    if configured.exists():
        return configured
    if configured != fallback:
        LOGGER.warning("Configured RM product path %s missing, falling back to %s", configured, fallback)
    return fallback


cfg = Config(
    env_prefix="TI_"
)  # not supporting .env files anymore because https://github.com/encode/starlette/discussions/2446

LOG_LEVEL: int = cfg("LOG_LEVEL", default=10, cast=int)
TEMPLATES_PATH: Path = cfg("TEMPLATES_PATH", cast=Path, default=Path(__file__).parent / "templates")

TAK_CERTS_FOLDER: Path = cfg("TAK_CERTS_FOLDER", cast=Path, default=Path("/opt/tak/data/certs/files"))
RMAPI_PERSISTENT_FOLDER: Path = cfg("RMAPI_PERSISTENT_FOLDER", cast=Path, default=Path("/data/persistent"))

PRODUCT_HTTPS_EPHEMERAL_PORT: int = cfg("PRODUCT_HTTPS_EPHEMERAL_PORT", cast=int, default=4627)
STREAM_SYNC_ENABLED: bool = cfg("STREAM_SYNC_ENABLED", cast=bool, default=False)
STREAM_SYNC_INTERVAL: float = cfg("STREAM_SYNC_INTERVAL", cast=float, default=60.0)
MTX_PRODUCT_NAME: str = cfg("MTX_PRODUCT_NAME", cast=str, default="mtx")
RM_API_MTLS_BASE_URL: str = cfg("RM_API_MTLS_BASE_URL", cast=str, default=read_rm_mtls_base_uri())
MTX_PRODUCT_API_BASE_URL: str = cfg(
    "MTX_PRODUCT_API_BASE_URL",
    cast=str,
    default=read_product_api_base("mtx"),
)
MTX_INTEROP_STREAMS_PATH: str = cfg("MTX_INTEROP_STREAMS_PATH", cast=str, default="/api/v1/interop/streams")
TAK_VIDEO_CLASSIFICATION: str = cfg("TAK_VIDEO_CLASSIFICATION", cast=str, default="UNCLASSIFIED")
RM_PRODUCT_CERT_PATH: Path = resolve_rm_product_path(
    cfg(
        "RM_PRODUCT_CERT_PATH",
        cast=Path,
        default=default_rm_product_cert_path(),
    ),
    default_rm_product_cert_path(),
)
RM_PRODUCT_KEY_PATH: Path = resolve_rm_product_path(
    cfg(
        "RM_PRODUCT_KEY_PATH",
        cast=Path,
        default=default_rm_product_key_path(),
    ),
    default_rm_product_key_path(),
)

# TAK vite asset graphical addons
VITE_ASSET_SET: str = cfg("VITE_ASSET_SET", cast=str, default="not_used_by_default")
VITE_ASSET_SET_TEMPLATES_FOLDER: Path = cfg(
    "VITE_ASSET_SET_TEMPLATES_FOLDER",
    cast=Path,
    default=TEMPLATES_PATH / "tak_viteassets",
)

# TAK mission package defaults. Available mission packages are defined here.
TAK_MISSIONPKG_ADDON_FOLDER: str = cfg("TAK_MISSIONPKG_ADDON_FOLDER", cast=str, default="default")
TAK_MISSIONPKG_TEMPLATES_FOLDER: Path = cfg(
    "TAK_MISSIONPKG_TEMPLATES_FOLDER",
    cast=Path,
    default=TEMPLATES_PATH / "tak_missionpkg",
)
TAK_MISSIONPKG_ENABLED_PACKAGES: list[Path] = [
    Path("atak"),
    Path("itak"),
    Path("tak-tracker"),
]

# TAK datapackage defaults. Default files and zip-folders are defined here and will be added to "Default-ATAK" profile
TAK_DATAPACKAGE_ADDON_FOLDER: str = cfg("TAK_DATAPACKAGE_ADDON_FOLDER", cast=str, default="default")
TAK_DATAPACKAGE_TEMPLATES_FOLDER: Path = cfg(
    "TAK_DATAPACKAGE_TEMPLATES_FOLDER",
    cast=Path,
    default=TEMPLATES_PATH / "tak_datapackage",
)

# Single files that are added to TAK as profile files
TAK_DATAPACKAGE_ADDON_FOLDER_FILES: list[Path] = []

# Folders that are added to TAK as zip profile packages.
TAK_DATAPACKAGE_ADDON_FOLDER_ZIP_PACKAGES: list[Path] = [
    Path("ATAK-default-settings"),
    Path("ATAK-TeamMember_Toolbar"),
    Path("Maps"),
    Path("Mesh-Encryption"),
    Path("Update-Server"),
]
# "ATAK-Toolbar",

TAK_MESSAGING_API_HOST: str = cfg("TAK_MESSAGING_API_HOST", cast=str, default="https://127.0.0.1")  # We are in sidecar
TAK_MESSAGING_API_PORT: int = cfg("TAK_MESSAGING_API_PORT", cast=int, default=8443)

TAKCL_CORECONFIG_PATH: Path = cfg("TAKCL_CORECONFIG_PATH", cast=Path, default=Path("/opt/tak/data/CoreConfig.xml"))

# Used for mission pkgs
MTX_SERVER_FQDN: str = cfg("MTX_SERVER_FQDN", cast=str, default="Not Available - ENV not set")
MTX_SERVER_SRT_PORT: int = cfg("MTX_SERVER_SRT_PORT", cast=int, default=8890)
MTX_SERVER_OBSERVER_PORT: int = cfg("MTX_SERVER_SRT_PORT", cast=int, default=8322)
MTX_SERVER_OBSERVER_PROTO: str = cfg("MTX_SERVER_OBSERVER_PROTO", cast=str, default="rtsps")
MTX_SERVER_OBSERVER_NET_PROTO: str = cfg("MTX_SERVER_OBSERVER_NET_PROTO", cast=str, default="tcp")
TAK_SERVER_FQDN: str = cfg("TAK_SERVER_FQDN", cast=str, default=read_tak_fqdn())
TAK_SERVER_NAME: str = cfg("TAK_SERVER_NAME", cast=str, default=read_deployment_name())
TAK_SERVER_NETWORKMESH_KEY_FILE: Path = cfg(
    "TAK_SERVER_NETWORKMESH_KEY_FILE", cast=Path, default=Path("/opt/tak/data/tak_server_networkmesh")
)

TAK_SERVER_NETWORKMESH_KEY_STR: str = ""  # tak_init sets this variable

AIRGUARD_API: str = cfg("AIRGUARD_API", cast=str, default="Not Available - ENV not set")
