"""Helper functions to manage tak datapackage templates"""

from typing import ClassVar
import logging
import hashlib
from pathlib import Path
import uuid
from dataclasses import dataclass

from takrmapi import config
from takrmapi.takutils.tak_helpers import UserCRUD


LOGGER = logging.getLogger(__name__)


@dataclass
class UserTAKTemplateVars:
    """TAK Template variable mapping to user/environment values"""

    user: UserCRUD
    template_file: Path

    # Deployment specific "static" var mapping for template files
    tak_server_deployment_name: ClassVar[str] = config.TAK_SERVER_NAME
    tak_server_public_address: ClassVar[str] = config.TAK_SERVER_FQDN
    mtx_server_public_address: ClassVar[str] = config.MTX_SERVER_FQDN
    mtx_server_srt_port: ClassVar[int] = config.MTX_SERVER_SRT_PORT
    mtx_server_observer_port: ClassVar[int] = config.MTX_SERVER_OBSERVER_PORT
    mtx_server_observer_proto: ClassVar[str] = config.MTX_SERVER_OBSERVER_PROTO
    mtx_server_observer_net_proto: ClassVar[str] = config.MTX_SERVER_OBSERVER_NET_PROTO

    @property
    def tak_userfile_uid(self) -> str:
        """Return UUID for users files"""
        return str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"{config.TAK_SERVER_FQDN}/{self.user.callsign}/{self.template_file}")
        )

    @property
    def client_cert_name(self) -> str:
        """User cert name mapping."""
        return self.user.callsign

    @property
    def client_cert_password(self) -> str:
        """User pw mapping for cert in templates,"""
        return self.user.callsign

    @property
    def tak_network_mesh_key(self) -> str:
        """ATAK mesh key mapping. Same for whole deployment."""
        return str(hashlib.sha256(config.TAK_SERVER_NETWORKMESH_KEY_STR.encode("utf-8")).hexdigest())

    @property
    def client_mtx_username(self) -> str:
        """TODO Return users MTX username"""
        return "TODO-Username_Retrieve_Not_Implemented_Yet"

    @property
    def client_mtx_password(self) -> str:
        """TODO Return users MTX username"""
        return "TODO-PW-Retrieve-Not-Implemented-Yet"
