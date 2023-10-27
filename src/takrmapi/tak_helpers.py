"""Helper functions to manage tak"""
import os
import asyncio
import shutil
import logging
from pathlib import Path
from typing import Any, Mapping, Union, cast
import aiohttp
import cryptography.x509
from cryptography.hazmat.primitives.serialization import (
    pkcs12,
    NoEncryption,
)
from OpenSSL import crypto

from libpvarki.mtlshelp.session import get_session as libsession
from jinja2 import Template
from takrmapi import config


LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 3.0


async def add_new_user(callsign: str = "", x509cert: str = "") -> bool:
    """Add new user to TAK with given certificate"""
    await user_cert_write(callsign=callsign, x509cert=x509cert)
    if await user_cert_validate(callsign=callsign):
        await add_user_to_tak_with_cert(callsign=callsign)
        return True
    return False


async def revoke_user(callsign: str = "") -> bool:
    """Remove user from TAK"""
    if await user_cert_validate(callsign=callsign):
        await delete_user_with_cert(callsign=callsign)
    # TODO REMOVE CERTIFICATE FROM config.TAK_CERTS_FOLDER
    return False


async def promote_user(callsign: str = "") -> bool:
    """Promote user to admin"""
    if await user_cert_validate(callsign=callsign):
        await add_admin_to_tak_with_cert(callsign=callsign)
        return True
    return False


async def demote_user(callsign: str = "") -> bool:
    """Demote user from being admin"""
    # TODO # THIS WORKS POORLY UNTIL PROPER REST IS FOUND OR SOME OTHER ALTERNATIVE
    # WE JUST RECREATE THE USER HERE AND GET RID OF THE ADMIN PERMISSIONS THAT WAY
    if await user_cert_validate(callsign=callsign):
        await delete_user_with_cert(callsign=callsign)
        await add_user_to_tak_with_cert(callsign=callsign)
        return True

    return False


async def update_user(callsign: str = "", x509cert: str = "") -> bool:
    """Update user certificate"""
    # TODO # THIS NEED TO BE CHECKED WHAT IT ACTUALLY DOES IN BACKGROUND,
    # DOES IT UPDATE THE CERTIFICATE OR ADD NEW USER OR WHAT??
    await user_cert_write(callsign=callsign, x509cert=x509cert)
    if await user_cert_validate(callsign=callsign):
        # TODO check/find out if the user is admin and add as admin
        await add_user_to_tak_with_cert(callsign=callsign)
    return False


async def create_missionpkg(callsign: str = "", missionpkg: str = config.TAK_MISSIONPKG_DEFAULT_MISSION) -> list[str]:
    """Create tak mission package packages to different app versions"""
    returnable: list[str] = []
    tmp_folder = f"{config.TAK_MISSIONPKG_TMP}/{callsign}_{missionpkg}"
    walk_dir = f"{config.TAK_MISSIONPKG_TEMPLATES_FOLDER}/{missionpkg}"
    await remove_tmp_dir(tmp_folder)
    os.makedirs(tmp_folder)
    if os.path.exists(f"{walk_dir}/atak"):
        zip_file = await create_mission_zip(
            app_version="atak", walk_dir=f"{walk_dir}/atak", callsign=callsign, missionpkg=missionpkg
        )
        returnable.append(zip_file)
    if os.path.exists(f"{walk_dir}/itak"):
        zip_file = await create_mission_zip(
            app_version="itak", walk_dir=f"{walk_dir}/itak", callsign=callsign, missionpkg=missionpkg
        )
        returnable.append(zip_file)

    return returnable


async def create_mission_zip(
    app_version: str = "", walk_dir: str = "", callsign: str = "", missionpkg: str = ""
) -> str:
    """Loop through files in"""
    # TODO maybe in memory fs for tmp files...

    tmp_folder = f"{config.TAK_MISSIONPKG_TMP}/{callsign}_{missionpkg}/{app_version}"
    os.makedirs(tmp_folder)
    for root, dirs, files in os.walk(walk_dir):
        for name in dirs:
            os.makedirs(f"{tmp_folder}{os.path.join(root, name).replace(walk_dir, '')}")

        for name in files:
            org_file = os.path.join(root, name)
            dst_file = f"{tmp_folder}{os.path.join(root, name).replace(walk_dir,'')}"

            if dst_file.endswith(".tpl"):
                with open(org_file, "r", encoding="utf-8") as filehandle:
                    template = Template(filehandle.read())

                rendered_template = await render_tak_manifest_template(template=template, callsign=callsign)
                new_dst_file = dst_file.replace(".tpl", "")
                if new_dst_file.endswith("manifest.xml"):
                    await tak_manifest_extra(rendered_template, callsign, tmp_folder)

                with open(new_dst_file, "w", encoding="utf-8") as filehandle:
                    filehandle.write(rendered_template)

            else:
                shutil.copy(org_file, dst_file)

    await zip_folder_content(tmp_folder, tmp_folder)

    # await remove_tmp_dir(tmp_folder)
    return f"{tmp_folder}.zip"


async def render_tak_manifest_template(template: Template, callsign: str = "") -> str:
    """Render tak manifest template"""
    return template.render(
        tak_server_uid_name="UID_NAME_TODO",
        tak_server_name="TAK_SRV_NAME_TODO",
        tak_server_address="SOME_TAK_ADDRESS",
        client_cert_name=callsign,
        client_cert_password=callsign,
    )


async def zip_folder_content(zipfile: str, tmp_folder: str) -> None:
    """Zip folder content"""
    shutil.make_archive(zipfile, "zip", tmp_folder)


async def tak_manifest_extra(manifest: str, callsign: str, tmp_folder: str) -> None:
    """Check if there is some extra that needs to be done defined in manfiest"""
    manifest_rows = manifest.splitlines()
    for row in manifest_rows:
        # .p12 rows
        # <!--
        if "<!--" in row:
            continue
        if ".p12" in row:
            await manifest_p12_row(row, callsign, tmp_folder)


async def manifest_p12_row(row: str, callsign: str, tmp_folder: str) -> None:
    """Handle manifest .p12 rows"""
    # Create .p12 from letsencrypt cert (/le_certs/rasenmaeher/fullchain.pem)
    if "takserver-public.p12" in row:
        LOGGER.info("Creating takserver-public.p12 file")
        dest_file: str = f"{tmp_folder}/content/takserver-public.p12"
        await write_pfx_just_cert(
            cert_file="/le_certs/rasenmaeher/fullchain.pem", callsign=callsign, dest_file=dest_file
        )


async def write_pfx_just_cert(cert_file: str, callsign: str, dest_file: str) -> None:
    """Write the manifest pfx"""
    cert = cryptography.x509.load_pem_x509_certificate(Path(cert_file).read_bytes())
    p12bytes = pkcs12.serialize_key_and_certificates(callsign.encode("utf-8"), None, cert, None, NoEncryption())
    Path(dest_file).write_bytes(p12bytes)


async def remove_tmp_dir(dirname: str = "") -> None:
    """Remove temporary folder"""
    if os.path.exists(dirname):
        shutil.rmtree(dirname)


async def tak_mtls_client() -> aiohttp.ClientSession:
    """Return session to connect TAK"""
    priv_key = config.RMAPI_PERSISTENT_FOLDER / "private" / "mtlsclient.key"
    pub_key = config.RMAPI_PERSISTENT_FOLDER / "public" / "mtlsclient.pem"
    return libsession((pub_key, priv_key))


def tak_base_url() -> str:
    """Construct the base url"""
    return f"{config.TAK_MESSAGING_API_HOST}:{config.TAK_MESSAGING_API_PORT}"


async def user_cert_exists(callsign: str = "") -> bool:
    """Check that the certificate exists"""
    cert_file = config.TAK_CERTS_FOLDER / f"{callsign}.pem"
    return cert_file.exists()


async def user_cert_write(callsign: str = "", x509cert: str = "") -> None:
    """Write users public cert to TAK certs folder"""
    cert_file_name = config.TAK_CERTS_FOLDER / f"{callsign}.pem"

    with open(cert_file_name, "w", encoding="utf-8") as cert_file:
        cert_file.write(x509cert.replace("\\n", "\n"))
        cert_file.write("\n")


async def user_cert_validate(callsign: str = "") -> bool:
    """Check that the given certificate can at least be opened"""
    try:
        cert_file_name = config.TAK_CERTS_FOLDER / f"{callsign}.pem"
        with open(cert_file_name, "rb") as cert_file:
            cert_content = cert_file.read()

        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_content)
        _ = cert.get_subject()
        _ = cert.get_issuer()
        return True
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.warning("User '{}' certificate check failed ::: {}".format(callsign, err))
        return False


# curl -k --cert public/mtlsclient.pem --key private/mtlsclient.key https://takmsg:8443/user-management/api/list-users
async def tak_api_user_list() -> Mapping[str, Any]:
    """Get list of users from TAK"""
    async with (await tak_mtls_client()) as session:
        try:
            url = f"{tak_base_url()}/user-management/api/list-users"
            resp = await session.get(url)
            data = cast(Mapping[str, Union[Any, Mapping[str, Any]]], await resp.json(content_type=None))
        except aiohttp.ClientError:
            return {}
    LOGGER.info("tak_api_user_list={}".format(data))
    return data


async def add_user_to_tak_with_cert(callsign: str = "") -> bool:
    """Add user to TAK. Certificate with callsign should be available by now..."""
    #
    # THIS SHOULD BE CHANGED TO BE DONE THROUGH REST IF POSSIBLE
    #
    environ = os.environ.copy()
    environ["TAKCL_CORECONFIG_PATH"] = str(config.TAKCL_CORECONFIG_PATH)
    environ["USER_CERT_NAME"] = callsign
    proc = await asyncio.create_subprocess_exec(
        "/opt/scripts/enable_user.sh", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=environ
    )

    stdout, stderr = await proc.communicate()
    LOGGER.info("useradd STDOUT: {!r}".format(stdout))
    LOGGER.info("useradd STDERR: {!r}".format(stderr))
    return True


async def add_admin_to_tak_with_cert(callsign: str = "") -> bool:
    """Add admin user to TAK using shell"""
    #
    # THIS SHOULD BE CHANGED TO BE DONE THROUGH REST IF POSSIBLE
    #
    environ = os.environ.copy()
    environ["ADMIN_CERT_NAME"] = callsign
    proc = await asyncio.create_subprocess_exec(
        "/opt/scripts/enable_admin.sh", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=environ
    )
    _, _ = await proc.communicate()
    return False


async def delete_user_with_cert(callsign: str = "") -> bool:
    """Add admin user to TAK using shell"""
    #
    # THIS SHOULD BE CHANGED TO BE DONE THROUGH REST IF POSSIBLE
    #
    environ = os.environ.copy()
    environ["ADMIN_CERT_NAME"] = callsign
    proc = await asyncio.create_subprocess_exec(
        "/opt/scripts/delete_user.sh", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=environ
    )
    _, _ = await proc.communicate()
    return False
