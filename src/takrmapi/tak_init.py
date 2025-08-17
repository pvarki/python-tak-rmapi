"""Init TAK management connection capability"""

import asyncio
import logging
import shutil
import secrets
import string
from pathlib import Path

from libpvarki.schemas.product import UserCRUDRequest
from takrmapi import config
from takrmapi import tak_helpers

LOGGER = logging.getLogger(__name__)


# CHECK FOR mtlsclient cert in tak cert folder /opt/tak/cert/files


async def setup_tak_mgmt_conn() -> None:
    """Setup required credentials to manage TAK"""
    # FIXME: Refactor to separate helpers not requiring a dummy user

    user: tak_helpers.UserCRUD = tak_helpers.UserCRUD(
        UserCRUDRequest(uuid="not_needed", callsign="mtlsclient", x509cert="not_needed")
    )
    t_helpers = tak_helpers.Helpers(user)
    t_rest_helper = tak_helpers.RestHelpers(user)

    # Wait for the TAK API to start responding
    for _ in range(60):
        data = await t_rest_helper.tak_api_user_list()

        if not data["success"]:
            LOGGER.info("TAK API not ready yet. Waiting...")
            LOGGER.info(data)
            await asyncio.sleep(5)  # nosec
        else:
            LOGGER.info("TAK API responding, moving on...")
            break

    # Move mtlsclient.pem in place if not there already
    if not await t_helpers.user_cert_exists():
        # Copy mtlsclient.pem from /data/persistent/public/mtlsclient.pem to
        new_filepath = config.TAK_CERTS_FOLDER / "mtlsclient.pem"
        shutil.copy("/data/persistent/public/mtlsclient.pem", new_filepath)
    else:
        LOGGER.info("mtlsclient cert already in place. No need to copy from /data/persistent...")

    # Check if we can already use TAK rest api. If not then add the mtlsinit as admin user
    data = await t_rest_helper.tak_api_user_list()
    if not data["data"]:
        LOGGER.info("Adding mtlsclient as administrator to TAK")
        await t_helpers.add_admin_to_tak_with_cert()
    else:
        LOGGER.info("Got user list, mtlsclient cert already added as admin")


async def setup_tak_defaults() -> None:
    """Set common required defaults to tak"""
    user: tak_helpers.UserCRUD = tak_helpers.UserCRUD(
        UserCRUDRequest(uuid="not_needed", callsign="mtlsclient", x509cert="not_needed")
    )
    t_rest_helper = tak_helpers.RestHelpers(user)

    LOGGER.info("Starting to set set TAK defaults")

    # Create environment specific networkMeshKey
    if not config.TAK_SERVER_NETWORKMESH_KEY_FILE.exists():
        mesh_str: str = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(64))
        config.TAK_SERVER_NETWORKMESH_KEY_FILE.write_text(mesh_str, encoding="utf-8")

    # Check that the "RECON" mission is available
    mission_recon_available = await t_rest_helper.tak_api_mission_get(groupname="RECON")

    if not mission_recon_available["data"]:
        mission_added = await t_rest_helper.tak_api_mission_put(
            groupname="RECON",
            description="Recon feed for validated information",
            default_role="MISSION_SUBSCRIBER",
        )

        if not mission_added["data"]:
            LOGGER.error("Unable to add RECON mission! Check takapi logs for possible errors.")
            return

        # Update mission keywords
        mission_keywords_added = await t_rest_helper.tak_api_mission_keywords(groupname="RECON", keywords=["#RECON"])
        if not mission_keywords_added:
            LOGGER.error("Unable to add keywords to RECON mission! Check takapi logs for possible errors.")
            return
    else:
        LOGGER.info("RECON mission already in place, no need to add again.")

    # Check that the "TAK-Defaults" profile is in place
    default_profile_available = await t_rest_helper.tak_api_get_device_profile(profile_name="Default-ATAK")
    LOGGER.info(default_profile_available)
    if "status" in default_profile_available["data"] and default_profile_available["data"]["status"] == "NOT_FOUND":
        LOGGER.info("Default-ATAK profile missing. Adding profile.")
        await t_rest_helper.tak_api_add_device_profile(profile_name="Default-ATAK", groups=["default"])
        await t_rest_helper.tak_api_update_device_profile(
            profile_name="Default-ATAK",
            profile_vars={
                "profile_active": True,
                "apply_on_connect": True,
                "apply_on_enrollment": False,
                "profile_type": "Connection",
                "tool": None,
                "groups": ["default"],
            },
        )
        await t_rest_helper.tak_api_upload_file_to_profile(
            profile_name="Default-ATAK",
            file_path=Path(
                config.TEMPLATES_PATH / "tak_datapackage" / "default" / "ATAK default settings" / "TAK_defaults.pref"
            ),
        )


async def get_tak_defaults() -> None:
    """Get common required defaults used in tak"""

    LOGGER.debug("Getting TAK defaults")
    # Read the tak server networkMeshKey to memory.
    while not config.TAK_SERVER_NETWORKMESH_KEY_FILE.exists():
        LOGGER.debug("Waiting for TAK_SERVER_NETWORKMESH_KEY_FILE to be populated")
        await asyncio.sleep(2)

    config.TAK_SERVER_NETWORKMESH_KEY_STR = config.TAK_SERVER_NETWORKMESH_KEY_FILE.read_text(encoding="utf-8")
