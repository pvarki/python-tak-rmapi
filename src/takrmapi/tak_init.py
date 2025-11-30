"""Init TAK management connection capability"""

import asyncio
import logging
import shutil
import secrets
import string
import tempfile
from pathlib import Path

from libpvarki.schemas.product import UserCRUDRequest
from takrmapi import config
from takrmapi import tak_helpers
from takrmapi.tak_helpers import UserCRUD, RestHelpers, MissionZip

LOGGER = logging.getLogger(__name__)


# CHECK FOR mtlsclient cert in tak cert folder /opt/tak/cert/files


async def setup_tak_mgmt_conn() -> None:
    """Setup required credentials to manage TAK"""
    # FIXME: Refactor to separate helpers not requiring a dummy user

    user: UserCRUD = UserCRUD(UserCRUDRequest(uuid="not_needed", callsign="mtlsclient", x509cert="not_needed"))
    t_helpers = tak_helpers.Helpers(user)
    t_rest_helper = RestHelpers(user)

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
    user: UserCRUD = UserCRUD(UserCRUDRequest(uuid="not_needed", callsign="mtlsclient", x509cert="not_needed"))
    t_rest_helper = RestHelpers(user)
    tak_missionpkg = MissionZip(user)

    LOGGER.info("Starting to set set TAK defaults")
    await tak_setup_mesh_key()
    await tak_setup_default_missions(t_rest_helper=t_rest_helper)
    await tak_setup_default_profiles(t_rest_helper=t_rest_helper)
    await tak_setup_profile_files(t_rest_helper=t_rest_helper, tak_missionpkg=tak_missionpkg)


async def tak_setup_mesh_key() -> None:
    """Create/load TAK network mesh key"""
    # Create environment specific networkMeshKey
    if not config.TAK_SERVER_NETWORKMESH_KEY_FILE.exists():
        mesh_str: str = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(64))
        config.TAK_SERVER_NETWORKMESH_KEY_FILE.write_text(mesh_str, encoding="utf-8")


async def tak_setup_default_missions(t_rest_helper: RestHelpers) -> None:
    """Create default TAK missions if missing"""
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


async def tak_setup_default_profiles(t_rest_helper: RestHelpers) -> None:
    """Create default TAK profiles"""
    # Check that the "TAK-Defaults" profile is in place
    default_profile_available = await t_rest_helper.tak_api_get_device_profile(profile_name="Default-ATAK")
    LOGGER.debug("Available TAK profiles: {}".format(default_profile_available))
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


async def tak_setup_profile_files(t_rest_helper: RestHelpers, tak_missionpkg: MissionZip) -> None:
    """Upload default tak profile files and bundles to TAK"""
    # Get current 'Default-ATAK' profile files
    profile_files = await t_rest_helper.tak_api_get_device_profile_files(profile_name="Default-ATAK")

    # Upload default files to profile
    for profile_file in config.TAK_DATAPACKAGE_DEFAULT_PROFILE_FILES:
        # Skip already uploaded files
        if await t_rest_helper.check_file_in_profile_files(
            local_profile_file=profile_file, tak_profile_files=profile_files
        ):
            continue

        if profile_file.name.endswith(".tpl"):
            profile_file_str = await tak_missionpkg.render_tak_manifest_template(profile_file)

            # TODO tmpfile in memory
            tmp_folder = Path(tempfile.mkdtemp(suffix="_INIT_TEMP"))
            tmp_template_file = tmp_folder / profile_file.name.replace(".tpl", "")

            with open(tmp_template_file, "w", encoding="utf-8") as filehandle:
                filehandle.write(profile_file_str)

            await t_rest_helper.tak_api_upload_file_to_profile(
                profile_name="Default-ATAK",
                file_path=tmp_template_file,
            )

            await tak_missionpkg.helpers.remove_tmp_dir(tmp_folder)

        else:
            await t_rest_helper.tak_api_upload_file_to_profile(
                profile_name="Default-ATAK",
                file_path=profile_file,
            )

    # Create zip bundles and upload to profile
    # First check for bundles already uploaded
    upload_bundles: list[Path] = []
    for bundle in config.TAK_DATAPACKAGE_DEFAULT_PROFILE_ZIP_PACKAGES:
        if await t_rest_helper.check_file_in_profile_files(local_profile_file=bundle, tak_profile_files=profile_files):
            continue
        upload_bundles.append(bundle)

    if len(upload_bundles) > 0:
        zip_files, tmp_folder = await tak_missionpkg.create_zip_bundles(
            template_folders=upload_bundles, is_mission_package=False
        )
        for file in zip_files:
            await t_rest_helper.tak_api_upload_file_to_profile(
                profile_name="Default-ATAK",
                file_path=file,
            )
        await tak_missionpkg.helpers.remove_tmp_dir(tmp_folder)


async def get_tak_defaults() -> None:
    """Get common required defaults used in tak"""

    LOGGER.debug("Getting TAK defaults")
    # Read the tak server networkMeshKey to memory.
    while not config.TAK_SERVER_NETWORKMESH_KEY_FILE.exists():
        LOGGER.debug("Waiting for TAK_SERVER_NETWORKMESH_KEY_FILE to be populated")
        await asyncio.sleep(2)

    config.TAK_SERVER_NETWORKMESH_KEY_STR = config.TAK_SERVER_NETWORKMESH_KEY_FILE.read_text(encoding="utf-8")
