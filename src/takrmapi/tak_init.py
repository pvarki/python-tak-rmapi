"""Init TAK management connection capability"""
import logging
import shutil

from takrmapi import config
from takrmapi import tak_helpers

LOGGER = logging.getLogger(__name__)

# CHECK FOR mtlsclient cert in tak cert folder /opt/tak/cert/files


async def setup_tak_mgmt_conn() -> None:
    """Setup required credentials to manage TAK"""
    # Move mtlsclient.pem in place if not there already
    if not await tak_helpers.user_cert_exists("mtlsclient"):
        # Copy mtlsclient.pem from /data/persistent/public/mtlsclient.pem to
        new_filepath = config.TAK_CERTS_FOLDER / "mtlsclient.pem"

        shutil.copy("/data/persistent/public/mtlsclient.pem", new_filepath)
    else:
        LOGGER.info("mtlsclient cert already in place. No need to copy from /data/persistent...")

    # Check if we can already use TAK rest api. If not then add the mtlsinit as admin user
    data = await tak_helpers.tak_api_user_list()
    if not data:
        LOGGER.info("Adding mtlsclient as administrator to TAK")
        await tak_helpers.add_admin_to_tak_with_cert("mtlsclient")
