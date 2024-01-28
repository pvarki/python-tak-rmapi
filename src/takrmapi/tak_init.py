"""Init TAK management connection capability"""
import logging
import shutil

from libpvarki.schemas.product import UserCRUDRequest
from takrmapi import config
from takrmapi import tak_helpers

LOGGER = logging.getLogger(__name__)


# CHECK FOR mtlsclient cert in tak cert folder /opt/tak/cert/files


async def setup_tak_mgmt_conn() -> None:
    """Setup required credentials to manage TAK"""
    # FIXME: Refactor to separate helpers not requiring a dummy user
    # FIXME: Use locking to not run this for each worker at the same time
    user: tak_helpers.UserCRUD = tak_helpers.UserCRUD(
        UserCRUDRequest(uuid="not_needed", callsign="mtlsclient", x509cert="not_needed")
    )
    t_helpers = tak_helpers.Helpers(user)
    t_rest_helper = tak_helpers.RestHelpers(user)

    # Move mtlsclient.pem in place if not there already
    if not await t_helpers.user_cert_exists():
        # Copy mtlsclient.pem from /data/persistent/public/mtlsclient.pem to
        new_filepath = config.TAK_CERTS_FOLDER / "mtlsclient.pem"
        shutil.copy("/data/persistent/public/mtlsclient.pem", new_filepath)
    else:
        LOGGER.info("mtlsclient cert already in place. No need to copy from /data/persistent...")

    # Check if we can already use TAK rest api. If not then add the mtlsinit as admin user
    data = await t_rest_helper.tak_api_user_list()
    if not data:
        LOGGER.info("Adding mtlsclient as administrator to TAK")
        await t_helpers.add_admin_to_tak_with_cert()
