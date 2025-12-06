"""Helper functions to manage tak data packages"""

from typing import ClassVar
import logging
from dataclasses import dataclass
from pathlib import Path
from takrmapi import config


LOGGER = logging.getLogger(__name__)
SHELL_TIMEOUT = 5.0
KEYPAIR_TIMEOUT = 5.0


@dataclass
class TAKDataPackageSiteVars:
    """TAK Datapackage site vars"""

    # Templating internal variables
    client_pkg_default_folder: ClassVar[Path] = (
        Path(config.TAK_DATAPACKAGE_TEMPLATES_FOLDER) / "default" / "client-packages"
    )
    client_pkg_extra_folder: ClassVar[Path] = (
        Path(config.TAK_DATAPACKAGE_TEMPLATES_FOLDER) / config.TAK_DATAPACKAGE_ADDON_FOLDER / "client-packages"
    )
    env_pkg_default_folder: ClassVar[Path] = (
        Path(config.TAK_DATAPACKAGE_TEMPLATES_FOLDER) / "default" / "environment-packages"
    )
    env_pkg_extra_folder: ClassVar[Path] = (
        Path(config.TAK_DATAPACKAGE_TEMPLATES_FOLDER) / config.TAK_DATAPACKAGE_ADDON_FOLDER / "environment-packages"
    )
    missionpkg_default_folder: ClassVar[Path] = Path(config.TAK_MISSIONPKG_TEMPLATES_FOLDER) / "default"
    missionpkg_extra_folder: ClassVar[Path] = (
        Path(config.TAK_MISSIONPKG_TEMPLATES_FOLDER) / config.TAK_MISSIONPKG_ADDON_FOLDER
    )
    extra_pkg_enabled: ClassVar[bool] = False
    extra_mission_enabled: ClassVar[bool] = False

    def __post_init__(self) -> None:
        """Template variables post init"""
        if config.TAK_DATAPACKAGE_ADDON_FOLDER != "default":
            TAKDataPackageSiteVars.extra_pkg_enabled = True

        if config.TAK_MISSIONPKG_ADDON_FOLDER != "default":
            TAKDataPackageSiteVars.extra_mission_enabled = True
