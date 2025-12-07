"""Helpers for TAK administrator actions"""

from typing import Dict, Any
from dataclasses import dataclass
from pathlib import Path
import logging

from takrmapi import config
from takrmapi.taktools.tak_helpers import UserCRUD
from takrmapi.taktools.tak_pkg_sitevars import TAKDataPackageSiteVars

LOGGER = logging.getLogger(__name__)


@dataclass
class TAKAdminHelper:
    """TAK admin helpers"""

    user: UserCRUD

    # TODO
    @property
    def check_user_permissions(self) -> bool:
        """Check if the user has permission to use elevated actions"""
        # TODO
        return True

    @property
    def get_available_datapackages(self) -> Dict[str, Any]:
        """Return available packages and files"""
        dir_content: Dict[str, Any] = {"default": self.get_dir_content(TAKDataPackageSiteVars.env_pkg_default_folder)}
        if TAKDataPackageSiteVars.extra_pkg_enabled:
            dir_content["extra"] = self.get_dir_content(TAKDataPackageSiteVars.env_pkg_extra_folder)

        dir_content["others"] = self.get_dir_content(Path(config.TAK_DATAPACKAGE_TEMPLATES_FOLDER) / "others")

        # And then the "special" ones
        dir_content["Role-Packages"] = self.get_dir_content(
            Path(config.TAK_DATAPACKAGE_TEMPLATES_FOLDER) / "others" / "Role-Colour-Packages" / "Roles"
        )
        dir_content["Colours-Packages"] = self.get_dir_content(
            Path(config.TAK_DATAPACKAGE_TEMPLATES_FOLDER) / "others" / "Role-Colour-Packages" / "Colours"
        )

        return dir_content

    def get_dir_content(self, dirpath: Path) -> Dict[str, Any]:
        """Get dir content"""
        dir_content: Dict[str, Any] = {}
        for item in dirpath.iterdir():
            if item.is_dir():
                dir_content[item.name] = "dir"
            else:
                dir_content[item.name] = "file"

        return dir_content
