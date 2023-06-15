"""Schema for CMD."""
from typing import Optional
from pydantic import BaseModel


class DoSomeThingIn(BaseModel):  # pylint: disable=too-few-public-methods
    """api cmd do something in schema"""

    cmd_str: str
    cmd_mode: str
    cmd_allow_semicolon: bool = False
    cmd_base64: bool = False
    docker_container_id: str = ""
    docker_interactive_exec: bool = False
    az_resource_group: str = ""
    az_container_group_name: str = ""
    az_container_name: str = ""

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": {
                "normal": {
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {
                        "cmd_str": "[str] - Command that will be issued through api",
                        "cmd_mode": "[str] - Endpoint mode, can be either local/docker/azure-container-service",
                        "cmd_allow_semicolon": "[opt][[bool] - Allow cmd_str to have semicolon(;), defaults to False",
                        "cmd_base64": "[opt][[bool] - cmd_str is base64 encoded, defaults to False",
                        "docker_container_id": "[opt][str] - ID/name for the container where command is issued.",
                        "docker_interactive_exec": "[opt][bool] - Set interactive flag for docker command",
                        "az_resource_group": "[opt][str] - Resource group name in azure container service",
                        "az_container_group_name": "[opt][str] - Container group name in azure container service",
                        "az_container_name": "[opt][str] - Container name in azure container service",
                    },
                },
                "with_local_values": {
                    "summary": "Example values for local cli command",
                    "description": "**Example** of values.",
                    "value": {
                        "cmd_str": "echo 'jaa joo ja jotain sellasta'",
                        "cmd_mode": "local",
                        "cmd_bas64": "False",
                    },
                },
                "with_docker_values": {
                    "summary": "Example values for docker cli command",
                    "description": "**Example** of values.",
                    "value": {
                        "cmd_str": "echo 'jaa joo ja jotain sellasta'",
                        "cmd_mode": "local",
                        "cmd_bas64": "False",
                        "docker_container_id": "Tunkki",
                    },
                },
                "with_docker_azure_values": {
                    "summary": "Example values for docker cli command azure container service",
                    "description": "**Example** of values.",
                    "value": {
                        "cmd_str": "echo 'jaa joo ja jotain sellasta'",
                        "cmd_mode": "local",
                        "cmd_bas64": "False",
                        "az_resource_group": "rg_some_rg_name",
                        "az_container_group_name": "mah-buckets",
                        "az_container_name": "Tunkki",
                    },
                },
            }
        }


class DoSomeThingOut(BaseModel):
    """api cmd do something out schema"""

    success: bool
    reason: str = ""
    rcode: int = 666
    stdout: str = ""
    stderr: str = ""

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
                "rcode": "[int] - return code. 666 for 'internal errors', 999 for Exception trace...",
                "stdout": "[str] - command output",
                "stderr": "[str] - command error output",
            }
        }


class LdapConnString(BaseModel):  # pylint: disable=too-few-public-methods
    """Utils / LDAP conn string schema"""

    ldap_conn_string: Optional[str]
    ldap_user: Optional[str]
    success: bool
    reason: Optional[str]
