"""Helper functions to manage tak"""

from typing import Any, Mapping, Union, Sequence, cast, Tuple, List
import os
import asyncio
import shutil
import logging
from pathlib import Path
import uuid
import tempfile

from glob import glob
import aiohttp
from OpenSSL import crypto  # FIXME: Move to python-cryptography for cert parsing
from jinja2 import Template
from libpvarki.schemas.product import UserCRUDRequest
from libpvarki.mtlshelp.session import get_session as libsession
from libpvarki.mtlshelp.pkcs12 import convert_pem_to_pkcs12
from libpvarki.mtlshelp.csr import async_create_keypair, async_create_client_csr
from libpvarki.shell import call_cmd

from takrmapi import config


LOGGER = logging.getLogger(__name__)
SHELL_TIMEOUT = 5.0
KEYPAIR_TIMEOUT = 5.0

# FIXME: Convert the helpers to dataclasses


class UserCRUD:
    """Helper class for tak_helpers"""

    def __init__(self, user: UserCRUDRequest):
        self.user: UserCRUDRequest = user
        self.userdata: Path = config.RMAPI_PERSISTENT_FOLDER / "users" / user.uuid
        self.helpers = Helpers(self)

    @property
    def callsign(self) -> str:
        """return the callsign"""
        return self.user.callsign

    @property
    def certcn(self) -> str:
        """return CN for the special cert"""
        return self.user.callsign

    @property
    def rm_certpem(self) -> str:
        """RASENMAEHER Cert contents as PEM"""
        return self.user.x509cert.replace("\\n", "\n")

    @property
    def certpath(self) -> Path:
        """Path to local cert"""
        return self.userdata / f"{self.certcn}.pem"

    @property
    def keypath(self) -> Path:
        """Path to local cert"""
        return self.userdata / f"{self.certcn}.key"

    async def wait_for_keypair(self) -> None:
        """Wait for keypair to be available"""
        while not self.certpath.exists() or not self.keypath.exists():
            LOGGER.debug("Waiting for {} / {}".format(self.certpath, self.keypath))
            LOGGER.debug("userdata contents: {}".format(list(self.userdata.rglob("*"))))
            await asyncio.sleep(0.5)

    @property
    def certpem(self) -> str:
        """Local TAK-specific cert contents as PEM (or RASENMAEHER cert if local is not available)"""
        LOGGER.debug("Checking if {} exists: {}".format(self.certpath, self.certpath.exists()))
        if self.certpath.exists():
            return self.certpath.read_text(encoding="utf-8")
        LOGGER.debug("userdata contents: {}".format(list(self.userdata.rglob("*"))))
        raise ValueError("Local cert {} not found".format(self.certpath))

    @property
    def certkey(self) -> str:
        """Cert private key contents as PEM"""
        LOGGER.debug("Checking if {} exists: {}".format(self.keypath, self.keypath.exists()))
        if self.keypath.exists():
            return self.keypath.read_text(encoding="utf-8")
        LOGGER.debug("userdata contents: {}".format(list(self.userdata.rglob("*"))))
        raise ValueError("Private key {} not found".format(self.keypath))

    @property
    def rm_base(self) -> str:
        """Return RASENMAEHER base url"""
        manifest = config.load_manifest()
        return cast(str, manifest["rasenmaeher"]["mtls"]["base_uri"])

    async def create_user_dir_and_files(self) -> None:
        """create the userdata path and make a new tak specific cert/keypair"""
        self.userdata.mkdir(parents=True, exist_ok=True)
        certcn = self.certcn
        privpath = self.userdata / f"{certcn}.key"
        pubpath = self.userdata / f"{certcn}.pub"
        csrpath = self.userdata / f"{certcn}.csr"
        certpath = self.userdata / f"{certcn}.pem"

        LOGGER.info("Creating TAK specific keypair: {} -> {} ".format(certcn, privpath))
        ckp = await async_create_keypair(privpath, pubpath)
        LOGGER.debug("async_create_keypair awaited {} exists: {}".format(privpath, privpath.exists()))
        csrpem = await async_create_client_csr(ckp, csrpath, {"CN": self.certcn})
        LOGGER.debug(
            "async_create_keypairasync_create_client_csr awaited {} exists: {}".format(csrpath, csrpath.exists())
        )

        async with await self.helpers.tak_mtls_client() as session:
            url = f"{self.rm_base}api/v1/product/sign_csr/mtls"
            LOGGER.debug("POSTing to {}".format(url))
            resp = await session.post(url, json={"csr": csrpem})
            resp.raise_for_status()
            payload = await resp.json()
            certpath.write_text(payload["certificate"], encoding="utf-8")
            LOGGER.info("signed cert written to {}".format(certpath))

    async def add_new_user(self) -> bool:
        """Add new user to TAK with given certificate"""
        await self.create_user_dir_and_files()
        await self.helpers.user_cert_write()
        if await self.helpers.user_cert_validate():
            await self.helpers.add_user_to_tak_with_cert()
            return True
        return False

    async def revoke_user(self) -> bool:
        """Remove user from TAK"""
        if await self.helpers.user_cert_validate():
            async with await self.helpers.tak_mtls_client() as session:
                url = f"{self.rm_base}api/v1/product/revoke/mtls"
                LOGGER.debug("POSTing cert to {}".format(url))
                resp = await session.post(url, json={"cert": self.certpem})
                LOGGER.debug("Got response: {}".format(resp))
                resp.raise_for_status()
                payload = await resp.json()
                LOGGER.debug("Got payload: {}".format(payload))
            await self.helpers.delete_user_with_cert()
            if (config.TAK_CERTS_FOLDER / f"{self.user.callsign}.pem").is_file():
                os.remove(config.TAK_CERTS_FOLDER / f"{self.user.callsign}.pem")
            return True
        return False

    async def _check_and_create_missing_user(self) -> bool:
        """check if user exists, if not try to create"""
        if await self.helpers.user_cert_validate():
            return True
        await self.add_new_user()
        if not await self.helpers.user_cert_validate():
            LOGGER.error("User still does not have a valid cert, something is fscked up")
            return False
        return True

    async def promote_user(self) -> bool:
        """Promote user to admin"""
        if await self._check_and_create_missing_user():
            return await self.helpers.add_admin_to_tak_with_cert()
        return False

    async def demote_user(self) -> bool:
        """Demote user from being admin"""
        # TODO # THIS WORKS POORLY UNTIL PROPER REST IS FOUND OR SOME OTHER ALTERNATIVE
        # WE JUST RECREATE THE USER HERE AND GET RID OF THE ADMIN PERMISSIONS THAT WAY
        if await self._check_and_create_missing_user():
            if not await self.helpers.delete_user_with_cert():
                return False
            return await self.helpers.add_user_to_tak_with_cert()
        return False

    async def update_user(self) -> bool:
        """Update user certificate"""
        # TODO # THIS NEED TO BE CHECKED WHAT IT ACTUALLY DOES IN BACKGROUND,
        # DOES IT UPDATE THE CERTIFICATE OR ADD NEW USER OR WHAT??
        if await self._check_and_create_missing_user():
            # TODO check/find out if the user is admin and add as admin
            return await self.helpers.add_user_to_tak_with_cert()
        return False


class MissionZip:
    """Mission package class"""

    def __init__(self, user: UserCRUD):
        self.user: UserCRUD = user
        self.helpers = Helpers(self.user)
        self.missionpkg = config.TAK_MISSIONPKG_DEFAULT_MISSION

    async def create_missionpkg(self) -> List[Path]:
        """Create tak mission package packages to different app versions"""
        missionzip_path_list: List[Path] = []

        # FIXME: Use Paths until absolutely have to convert to strings
        tmp_folder = Path(tempfile.mkdtemp(suffix=f"_{self.user.callsign}_{self.missionpkg}"))
        walk_dir = Path(config.TAK_MISSIONPKG_TEMPLATES_FOLDER) / self.missionpkg
        tasks: List[asyncio.Task[Any]] = []
        # FIXME: maybe just do this dynamically for all subdirs under templates ?
        if os.path.exists(f"{walk_dir}/atak"):
            zip_file = await self.create_mission_zip(app_version="atak", walk_dir=f"{walk_dir}/atak")
            missionzip_path_list.append(zip_file)
        if os.path.exists(f"{walk_dir}/itak"):
            zip_file = await self.create_mission_zip(app_version="itak", walk_dir=f"{walk_dir}/itak")
            missionzip_path_list.append(zip_file)
        if os.path.exists(f"{walk_dir}/tak-tracker"):
            zip_file = await self.create_mission_zip(app_version="tak-tracker", walk_dir=f"{walk_dir}/tak-tracker")
            missionzip_path_list.append(zip_file)
        return missionzip_path_list

    async def create_mission_zip(self, app_version: str = "", walk_dir: str = "") -> Path:
        """Loop through files in missionpkg templates folder"""
        # TODO maybe in memory fs for tmp files...

        # TODO change strings to Paths
        tmp_folder: Path = Path(config.TAK_MISSIONPKG_TMP) / f"{self.user.callsign}_{self.missionpkg}/{app_version}"
        os.makedirs(tmp_folder)
        for root, dirs, files in os.walk(walk_dir):
            for name in dirs:
                dirpath = f"{tmp_folder}{os.path.join(root, name).replace(str(walk_dir), '')}"
                LOGGER.debug("Calling os.makedirs({})".format(dirpath))
                os.makedirs(dirpath)

            for name in files:
                org_file = os.path.join(root, name)
                dst_file = f"{tmp_folder}{os.path.join(root, name).replace(str(walk_dir),'')}"
                LOGGER.debug("org_file={} dst_file={}".format(org_file, dst_file))

                if dst_file.endswith(".tpl"):
                    with open(org_file, "r", encoding="utf-8") as filehandle:
                        template = Template(filehandle.read())

                    rendered_template = await self.render_tak_manifest_template(
                        template=template, app_version=app_version
                    )
                    new_dst_file = dst_file.replace(".tpl", "")
                    if new_dst_file.endswith("manifest.xml"):
                        await self.tak_manifest_extra(rendered_template, str(tmp_folder))
                    # For itak use blueteam.pref.tpl
                    if app_version == "itak" and new_dst_file.endswith("blueteam.pref"):
                        await self.tak_manifest_extra(rendered_template, str(tmp_folder))

                    with open(new_dst_file, "w", encoding="utf-8") as filehandle:
                        filehandle.write(rendered_template)

                else:
                    shutil.copy(org_file, dst_file)

        await self.zip_folder_content(str(tmp_folder), str(tmp_folder))

        # await remove_tmp_dir(tmp_folder)
        return Path(f"{tmp_folder}.zip")

    async def render_tak_manifest_template(self, template: Template, app_version: str) -> Any:
        """Render tak manifest template"""
        pkguid = uuid.uuid5(uuid.NAMESPACE_URL, f"{config.TAK_SERVER_FQDN}/{self.user.user.uuid}/{app_version}")
        return template.render(
            tak_server_uid_name=str(pkguid),
            tak_server_name=config.TAK_SERVER_NAME,
            tak_server_address=config.TAK_SERVER_FQDN,
            client_cert_name=self.user.callsign,
            client_cert_password=self.user.callsign,
        )

    async def zip_folder_content(self, zipfile: Path, tmp_folder: Path) -> None:
        """Zip folder content"""
<<<<<<< HEAD
        await asyncio.get_running_loop().run_in_executor(None, shutil.make_archive, zipfile, "zip", tmp_folder)
=======
        shutil.make_archive(str(zipfile), "zip", str(tmp_folder))
>>>>>>> 1f2138f... str->path started

    async def tak_manifest_extra(self, manifest: str, tmp_folder: Path) -> None:
        """Check if there is some extra that needs to be done defined in manfiest"""
        manifest_rows = manifest.splitlines()
        for row in manifest_rows:
            # .p12 rows
            # <!--
            if "<!--" in row:
                continue
            if ".p12" in row:
                await self.manifest_p12_row(row, tmp_folder)

    async def manifest_p12_row(self, row: str, tmp_folder: Path) -> None:
        """Handle manifest .p12 rows"""
        tmp_folder = await self.chk_manifest_file_extra_folder(row=row, tmp_folder=tmp_folder)
        # FIXME: do the blocking IO in executor
        if "rasenmaeher_ca-public.p12" in row:
            # FIXME: instead of adding the root key into the software, need a way to get full chain with Root CA
            templates_folder = Path(__file__).parent / "templates"
            ca_files = sorted(glob(f"{templates_folder}/*.pem"))
            srcdata = Path("/le_certs/rasenmaeher/fullchain.pem").read_bytes()
            if ca_files:
                for ca_f in ca_files:
                    srcdata = srcdata + Path(ca_f).read_bytes()

            tgtfile = Path(tmp_folder) / "rasenmaeher_ca-public.p12"
            LOGGER.info("Creating {}".format(tgtfile))
            p12bytes = convert_pem_to_pkcs12(srcdata, None, "public", None, "ca-chains")
            tgtfile.parent.mkdir(parents=True, exist_ok=True)
            LOGGER.debug("{} exists: {}".format(tgtfile.parent, tgtfile.parent.exists()))
            tgtfile.write_bytes(p12bytes)
            LOGGER.debug("{} exists: {}".format(tgtfile, tgtfile.exists()))
        elif f"{self.user.callsign}.p12" in row:
            tgtfile = Path(tmp_folder) / f"{self.user.callsign}.p12"
            await asyncio.wait_for(self.user.wait_for_keypair(), timeout=KEYPAIR_TIMEOUT)
            LOGGER.info("Creating {}".format(tgtfile))
            p12bytes = convert_pem_to_pkcs12(
                self.user.certpem, self.user.certkey, self.user.callsign, None, self.user.callsign
            )
            tgtfile.parent.mkdir(parents=True, exist_ok=True)
            tgtfile.write_bytes(p12bytes)
            LOGGER.debug("{} exists: {}".format(tgtfile, tgtfile.exists()))
        else:
            raise RuntimeError("IDK what to do")

    async def chk_manifest_file_extra_folder(self, row: str, tmp_folder: Path) -> Path:
        """Check folder path from manifest, return updated path if folder was located"""
        xml_value: str = row.split(">")[1].split("<")[0]
        if "/" in xml_value:
            manifest_file = tmp_folder / xml_value
            manifest_file.parent.mkdir(parents=True, exist_ok=True)
            LOGGER.info("File defined in manifest in folder {}".format(manifest_file.parent.absolute()))
            return Path(manifest_file.parent.absolute())
        return tmp_folder


class Helpers:
    """Helper class for tak management"""

    def __init__(self, user: UserCRUD):
        """Helpers init"""
        self.user: UserCRUD = user

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
        await asyncio.wait_for(self.user.wait_for_keypair(), timeout=KEYPAIR_TIMEOUT)
        cert_file_name = config.TAK_CERTS_FOLDER / f"{self.user.callsign}.pem"
        cert_file_name.write_text(self.user.certpem + "\n", encoding="utf-8")
        cert_file_name2 = config.TAK_CERTS_FOLDER / f"{self.user.callsign}_rm.pem"
        cert_file_name2.write_text(self.user.rm_certpem + "\n", encoding="utf-8")

    async def user_cert_validate(self) -> bool:
        """Check that the given certificate can at least be opened"""
        try:
            await self.user_cert_write()
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

    @property
    def enable_user_cert_names(self) -> Sequence[str]:
        """Return the stems for cert PEM files"""
        return (self.user.callsign, f"{self.user.callsign}_rm")

    async def add_user_to_tak_with_cert(self) -> bool:
        """Add user to TAK. Certificate with callsign should be available by now..."""
        #
        # THIS SHOULD BE CHANGED TO BE DONE THROUGH REST IF POSSIBLE
        # Or via Pyjnius, or via PyIgnite
        #
        if not await self.user_cert_validate():
            LOGGER.error("User {} TAK certs not valid".format(self.user.callsign))
            return False
        tasks = []
        for certname in self.enable_user_cert_names:
            tasks.append(
                asyncio.shield(
                    call_cmd(
                        f"USER_CERT_NAME={certname} /opt/scripts/enable_user.sh",
                        timeout=SHELL_TIMEOUT,
                        stderr_warn=False,
                    )
                )
            )
        try:
            results = await asyncio.gather(*tasks)
            for code, _stdout, _stderr in results:
                if code != 0:
                    return False
        except asyncio.TimeoutError:
            LOGGER.error("Shell command timed out")
            return False
        except asyncio.CancelledError:
            LOGGER.info("Cancellation shielded, just wait")
        except Exception as err:  # pylint: disable=W0718
            LOGGER.exception(err)
            return False
        return True

    async def add_admin_to_tak_with_cert(self) -> bool:
        """Add admin user to TAK using shell"""
        #
        # THIS SHOULD BE CHANGED TO BE DONE THROUGH REST IF POSSIBLE
        # Or via Pyjnius, or via PyIgnite
        #
        if not await self.user_cert_validate():
            LOGGER.error("User {} TAK certs not valid".format(self.user.callsign))
            return False
        tasks = []
        for certname in self.enable_user_cert_names:
            tasks.append(
                asyncio.shield(
                    call_cmd(
                        f"ADMIN_CERT_NAME={certname} /opt/scripts/enable_admin.sh",
                        timeout=SHELL_TIMEOUT,
                        stderr_warn=False,
                    )
                )
            )
        try:
            results = await asyncio.gather(*tasks)
            for code, _stdout, _stderr in results:
                if code != 0:
                    return False
        except asyncio.TimeoutError:
            LOGGER.error("Shell command timed out")
            return False
        except asyncio.CancelledError:
            LOGGER.info("Cancellation shielded, just wait")
        except Exception as err:  # pylint: disable=W0718
            LOGGER.exception(err)
            return False
        return True

    async def delete_user_with_cert(self) -> bool:
        """Remove user from TAK using shell"""
        #
        # THIS SHOULD BE CHANGED TO BE DONE THROUGH REST IF POSSIBLE
        # Or via Pyjnius, or via PyIgnite
        #
        if not await self.user_cert_validate():
            LOGGER.error("User {} TAK certs not valid".format(self.user.callsign))
            return False
        tasks = []
        for certname in self.enable_user_cert_names:
            tasks.append(
                asyncio.shield(
                    call_cmd(
                        f"USER_CERT_NAME={certname} /opt/scripts/delete_user.sh",
                        timeout=SHELL_TIMEOUT,
                        stderr_warn=False,
                    )
                )
            )
        try:
            results = await asyncio.gather(*tasks)
            for code, _stdout, _stderr in results:
                if code != 0:
                    return False
        except asyncio.TimeoutError:
            LOGGER.error("Shell command timed out")
            return False
        except asyncio.CancelledError:
            LOGGER.info("Cancellation shielded, just wait")
        except Exception as err:  # pylint: disable=W0718
            LOGGER.exception(err)
            return False
        return True


class RestHelpers:  # pylint: disable=too-few-public-methods
    """Helper class to make queries against TAK rest API"""

    # FIXME: Refactor to separate helpers not requiring a dummy user
    def __init__(
        self,
        user: UserCRUD = UserCRUD(
            UserCRUDRequest(uuid="not_used_now", callsign="not_used_now", x509cert="not_used_now")
        ),
    ):
        """RestHelpers init"""
        self.helpers = Helpers(user)

    # curl -k --cert public/mtlsclient.pem --key private/mtlsclient.key
    # https://takmsg:8443/user-management/api/list-users
    async def tak_api_user_list(self) -> Mapping[str, Any]:
        """Get list of users from TAK"""
        async with await self.helpers.tak_mtls_client() as session:
            try:
                url = f"{self.helpers.tak_base_url()}/user-management/api/list-users"
                resp = await session.get(url)
                data = cast(Mapping[str, Union[Any, Mapping[str, Any]]], await resp.json(content_type=None))
            except aiohttp.ClientError:
                return {}
        LOGGER.info("tak_api_user_list={}".format(data))
        return data
