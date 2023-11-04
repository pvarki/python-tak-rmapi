"""Helper functions to manage tak"""
from typing import Any, Mapping, Union, cast
import os
import asyncio
import shutil
import logging
from pathlib import Path
import aiohttp


import cryptography.x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import (
    pkcs12,
    PrivateFormat,
)
from OpenSSL import crypto  # FIXME: Move to python-cryptography for cert parsing
from jinja2 import Template
from libpvarki.schemas.product import UserCRUDRequest
from libpvarki.mtlshelp.session import get_session as libsession


from takrmapi import config


LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 3.0


class UserCRUD:
    """Helper class for tak_helpers"""

    def __init__(self, user: UserCRUDRequest):
        self.user: UserCRUDRequest = user
        self.helpers = Helpers(self.user)

    async def add_new_user(self) -> bool:
        """Add new user to TAK with given certificate"""
        await self.helpers.user_cert_write()
        if await self.helpers.user_cert_validate():
            await self.helpers.add_user_to_tak_with_cert()
            return True
        return False

    async def revoke_user(self) -> bool:
        """Remove user from TAK"""
        if await self.helpers.user_cert_validate():
            await self.helpers.delete_user_with_cert()
            if (config.TAK_CERTS_FOLDER / f"{self.user.callsign}.pem").is_file():
                os.remove(config.TAK_CERTS_FOLDER / f"{self.user.callsign}.pem")
            return True
        return False

    async def promote_user(self) -> bool:
        """Promote user to admin"""
        if await self.helpers.user_cert_validate():
            await self.helpers.add_admin_to_tak_with_cert()
            return True
        return False

    async def demote_user(self) -> bool:
        """Demote user from being admin"""
        # TODO # THIS WORKS POORLY UNTIL PROPER REST IS FOUND OR SOME OTHER ALTERNATIVE
        # WE JUST RECREATE THE USER HERE AND GET RID OF THE ADMIN PERMISSIONS THAT WAY
        if await self.helpers.user_cert_validate():
            await self.helpers.delete_user_with_cert()
            await self.helpers.add_user_to_tak_with_cert()
            return True

        return False

    async def update_user(self) -> bool:
        """Update user certificate"""
        # TODO # THIS NEED TO BE CHECKED WHAT IT ACTUALLY DOES IN BACKGROUND,
        # DOES IT UPDATE THE CERTIFICATE OR ADD NEW USER OR WHAT??
        await self.helpers.user_cert_write()
        if await self.helpers.user_cert_validate():
            # TODO check/find out if the user is admin and add as admin
            await self.helpers.add_user_to_tak_with_cert()
            return True
        return False


class MissionZip:
    """Mission package class"""

    def __init__(self, user: UserCRUDRequest):
        self.user: UserCRUDRequest = user
        self.helpers = Helpers(self.user)
        self.missionpkg = config.TAK_MISSIONPKG_DEFAULT_MISSION

    async def create_missionpkg(self) -> list[str]:
        """Create tak mission package packages to different app versions"""
        returnable: list[str] = []
        # FIXME: Use Paths until absolutely have to convert to strings
        tmp_folder = f"{config.TAK_MISSIONPKG_TMP}/{self.user.callsign}_{self.missionpkg}"
        walk_dir = f"{config.TAK_MISSIONPKG_TEMPLATES_FOLDER}/{self.missionpkg}"
        await self.helpers.remove_tmp_dir(tmp_folder)
        os.makedirs(tmp_folder)
        if os.path.exists(f"{walk_dir}/atak"):
            zip_file = await self.create_mission_zip(app_version="atak", walk_dir=f"{walk_dir}/atak")
            returnable.append(zip_file)
        if os.path.exists(f"{walk_dir}/itak"):
            zip_file = await self.create_mission_zip(app_version="itak", walk_dir=f"{walk_dir}/itak")
            returnable.append(zip_file)

        return returnable

    async def create_mission_zip(self, app_version: str = "", walk_dir: str = "") -> str:
        """Loop through files in missionpkg templates folder"""
        # TODO maybe in memory fs for tmp files...

        tmp_folder = f"{config.TAK_MISSIONPKG_TMP}/{self.user.callsign}_{self.missionpkg}/{app_version}"
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

                    rendered_template = await self.render_tak_manifest_template(template=template)
                    new_dst_file = dst_file.replace(".tpl", "")
                    if new_dst_file.endswith("manifest.xml"):
                        await self.tak_manifest_extra(rendered_template, tmp_folder)

                    with open(new_dst_file, "w", encoding="utf-8") as filehandle:
                        filehandle.write(rendered_template)

                else:
                    shutil.copy(org_file, dst_file)

        await self.zip_folder_content(tmp_folder, tmp_folder)

        # await remove_tmp_dir(tmp_folder)
        return f"{tmp_folder}.zip"

    async def render_tak_manifest_template(self, template: Template) -> str:
        """Render tak manifest template"""
        return template.render(
            tak_server_uid_name=config.TAK_SERVER_FQDN,
            tak_server_name=config.TAK_SERVER_NAME,
            tak_server_address=config.TAK_SERVER_FQDN,
            client_cert_name=self.user.callsign,
            client_cert_password=self.user.callsign,
        )

    async def zip_folder_content(self, zipfile: str, tmp_folder: str) -> None:
        """Zip folder content"""
        shutil.make_archive(zipfile, "zip", tmp_folder)

    async def tak_manifest_extra(self, manifest: str, tmp_folder: str) -> None:
        """Check if there is some extra that needs to be done defined in manfiest"""
        manifest_rows = manifest.splitlines()
        for row in manifest_rows:
            # .p12 rows
            # <!--
            if "<!--" in row:
                continue
            if ".p12" in row:
                await self.manifest_p12_row(row, tmp_folder)

    async def manifest_p12_row(self, row: str, tmp_folder: str) -> None:
        """Handle manifest .p12 rows"""
        dest_file: str = ""
        # Create .p12 from letsencrypt cert (/le_certs/rasenmaeher/fullchain.pem)
        if "rasenmaeher_ca-public.p12" in row:
            LOGGER.info("Creating rasenmaeher_ca-public.p12 file")
            dest_file = f"{tmp_folder}/content/rasenmaeher_ca-public.p12"
            if not os.path.exists(f"{tmp_folder}/content"):
                os.makedirs(f"{tmp_folder}/content")
            await self.write_pfx_just_cert(cert_file="/ca_public/ca_chain.pem", dest_file=dest_file)
        if f"{self.user.callsign}.p12" in row:
            LOGGER.info("DISABLED - Creating {}.p12 file".format(self.user.callsign))
            # dest_file = f"{tmp_folder}/content/{ self.user.callsign }.p12"
            # await self.write_pfx(
            #    cert_file=f"{config.TAK_CERTS_FOLDER}/{self.user.callsign}.pem",
            #    dest_file=dest_file,
            # )

    async def write_pfx_just_cert(self, cert_file: Union[str, Path], dest_file: Union[str, Path]) -> None:
        """Write the server certificate pfx"""
        cert_file = Path(cert_file)
        dest_file = Path(dest_file)
        cert = cryptography.x509.load_pem_x509_certificate(cert_file.read_bytes())
        key = None

        # Apple devices (and some windowses too I guess) have an issue with the modern
        # secure ways to encrypt pkcs12 files so we do it oldskool.
        encryption = (
            PrivateFormat.PKCS12.encryption_builder()
            .kdf_rounds(50000)
            .key_cert_algorithm(pkcs12.PBES.PBESv1SHA1And3KeyTripleDESCBC)  # nosec
            .hmac_hash(hashes.SHA1())  # nosec
            .build(b"public")
        )

        p12bytes = pkcs12.serialize_key_and_certificates(cert_file.stem.encode("utf-8"), key, cert, None, encryption)
        dest_file.write_bytes(p12bytes)


class Helpers:
    """Helper class for tak management"""

    def __init__(self, user: UserCRUDRequest):
        """Helpers init"""
        self.user: UserCRUDRequest = user

    async def remove_tmp_dir(self, dirname: str = "") -> None:
        """Remove temporary folder"""
        if os.path.exists(dirname):
            shutil.rmtree(dirname)

    async def tak_mtls_client(self) -> aiohttp.ClientSession:
        """Return session to connect TAK"""
        priv_key = config.RMAPI_PERSISTENT_FOLDER / "private" / "mtlsclient.key"
        pub_key = config.RMAPI_PERSISTENT_FOLDER / "public" / "mtlsclient.pem"
        return libsession((pub_key, priv_key))

    def tak_base_url(self) -> str:
        """Construct the base url"""
        return f"{config.TAK_MESSAGING_API_HOST}:{config.TAK_MESSAGING_API_PORT}"

    async def user_cert_exists(self) -> bool:
        """Check that the certificate exists"""
        cert_file = config.TAK_CERTS_FOLDER / f"{self.user.callsign}.pem"
        return cert_file.exists()

    async def user_cert_write(self) -> None:
        """Write users public cert to TAK certs folder"""
        cert_file_name = config.TAK_CERTS_FOLDER / f"{self.user.callsign}.pem"

        with open(cert_file_name, "w", encoding="utf-8") as cert_file:
            cert_file.write(self.user.x509cert.replace("\\n", "\n"))
            cert_file.write("\n")

    async def user_cert_validate(self) -> bool:
        """Check that the given certificate can at least be opened"""
        try:
            cert_file_name = config.TAK_CERTS_FOLDER / f"{self.user.callsign}.pem"
            with open(cert_file_name, "rb") as cert_file:
                cert_content = cert_file.read()

            cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_content)
            _ = cert.get_subject()
            _ = cert.get_issuer()
            return True
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.warning("User '{}' certificate check failed ::: {}".format(self.user.callsign, err))
            return False

    async def add_user_to_tak_with_cert(self) -> bool:
        """Add user to TAK. Certificate with callsign should be available by now..."""
        #
        # THIS SHOULD BE CHANGED TO BE DONE THROUGH REST IF POSSIBLE
        #
        environ = os.environ.copy()
        environ["TAKCL_CORECONFIG_PATH"] = str(config.TAKCL_CORECONFIG_PATH)
        environ["USER_CERT_NAME"] = self.user.callsign
        proc = await asyncio.create_subprocess_exec(
            "/opt/scripts/enable_user.sh", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=environ
        )

        stdout, stderr = await proc.communicate()
        LOGGER.info("useradd STDOUT: {!r}".format(stdout))
        LOGGER.info("useradd STDERR: {!r}".format(stderr))
        return True

    async def add_admin_to_tak_with_cert(self) -> bool:
        """Add admin user to TAK using shell"""
        #
        # THIS SHOULD BE CHANGED TO BE DONE THROUGH REST IF POSSIBLE
        #
        environ = os.environ.copy()
        environ["TAKCL_CORECONFIG_PATH"] = str(config.TAKCL_CORECONFIG_PATH)
        environ["ADMIN_CERT_NAME"] = self.user.callsign
        proc = await asyncio.create_subprocess_exec(
            "/opt/scripts/enable_admin.sh", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=environ
        )
        _, _ = await proc.communicate()
        return False

    async def delete_user_with_cert(self) -> bool:
        """Add admin user to TAK using shell"""
        #
        # THIS SHOULD BE CHANGED TO BE DONE THROUGH REST IF POSSIBLE
        #
        environ = os.environ.copy()
        environ["TAKCL_CORECONFIG_PATH"] = str(config.TAKCL_CORECONFIG_PATH)
        environ["USER_CERT_NAME"] = self.user.callsign
        proc = await asyncio.create_subprocess_exec(
            "/opt/scripts/delete_user.sh", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=environ
        )
        _, _ = await proc.communicate()
        return False


class RestHelpers:  # pylint: disable=too-few-public-methods
    """Helper class to make queries against TAK rest API"""

    def __init__(
        self,
        user: UserCRUDRequest = UserCRUDRequest(uuid="not_used_now", callsign="not_used_now", x509cert="not_used_now"),
    ):
        """RestHelpers init"""
        self.helpers = Helpers(user)

    # curl -k --cert public/mtlsclient.pem --key private/mtlsclient.key
    # https://takmsg:8443/user-management/api/list-users
    async def tak_api_user_list(self) -> Mapping[str, Any]:
        """Get list of users from TAK"""
        async with (await self.helpers.tak_mtls_client()) as session:
            try:
                url = f"{self.helpers.tak_base_url()}/user-management/api/list-users"
                resp = await session.get(url)
                data = cast(Mapping[str, Union[Any, Mapping[str, Any]]], await resp.json(content_type=None))
            except aiohttp.ClientError:
                return {}
        LOGGER.info("tak_api_user_list={}".format(data))
        return data
