"""Helper functions to manage tak"""

from typing import Sequence, cast
import os
import re
import asyncio
import shlex
import shutil
import logging
from pathlib import Path
import ssl

import aiohttp
from cryptography import x509

from libpvarki.schemas.product import UserCRUDRequest
from libpvarki.mtlshelp.session import get_session as libsession
from libpvarki.mtlshelp.csr import async_create_keypair, async_create_client_csr
from libpvarki.shell import call_cmd


from takrmapi import config
from takrmapi.takutils.env_helpers import env_float

LOGGER = logging.getLogger(__name__)

SHELL_TIMEOUT = env_float("TAK_RMAPI_SHELL_TIMEOUT", 5.0, max_value=600.0)
# UserManager.jar starts a JVM, which on a loaded host takes far longer than the
# general shell timeout. At 5s it timed out in production every time: the user was
# created by enable_user.sh and then left in __ANON__ because the group call never
# completed, which CoreConfig's x509addAnonymous="false" then refuses.
JVM_TIMEOUT = env_float("TAK_RMAPI_JVM_TIMEOUT", 60.0, max_value=600.0)
KEYPAIR_TIMEOUT = env_float("TAK_RMAPI_KEYPAIR_TIMEOUT", 5.0, max_value=600.0)

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


class Helpers:
    """Helper class for tak management"""

    def __init__(self, user: UserCRUD):
        """Helpers init"""
        self.user: UserCRUD = user

    async def remove_tmp_dir(self, dirname: Path) -> None:
        """Remove temporary folder"""
        if dirname.exists():
            shutil.rmtree(dirname)
            LOGGER.debug("Temp directory cleanup done.")

    async def tak_mtls_client(self) -> aiohttp.ClientSession:
        """Return session to connect TAK"""
        priv_key = config.RMAPI_PERSISTENT_FOLDER / "private" / "mtlsclient.key"
        pub_key = config.RMAPI_PERSISTENT_FOLDER / "public" / "mtlsclient.pem"
        return libsession((pub_key, priv_key))

    async def tak_mtls_client_sslcontext(self) -> ssl.SSLContext:
        """Return sslcontext to connect TAK"""
        sslcontext = ssl.create_default_context()
        sslcontext.check_hostname = False
        sslcontext.verify_mode = ssl.CERT_NONE
        sslcontext.load_cert_chain(
            config.RMAPI_PERSISTENT_FOLDER / "public" / "mtlsclient.pem",
            config.RMAPI_PERSISTENT_FOLDER / "private" / "mtlsclient.key",
        )
        return sslcontext

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
            if self.user.callsign != "mtlsclient":
                await self.user_cert_write()
            cert_file_name = config.TAK_CERTS_FOLDER / f"{self.user.callsign}.pem"
            with open(cert_file_name, "rb") as cert_file:
                cert_content = cert_file.read()

            cert = x509.load_pem_x509_certificate(cert_content)
            _ = cert.subject
            _ = cert.issuer
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
            if certname == "mtlsclient_rm":
                continue
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


# One enrolment at a time. The peer retries while it is failing and each attempt
# spawns a JVM: production logged nine overlapping enrolments inside 0.7s, which is
# the surest way to make the very timeout that caused the retries worse.
_ENROL_LOCK = asyncio.Lock()


# certcn becomes a filename AND part of a /bin/sh -c command line below. Anything outside
# this charset is rejected rather than escaped: a CN is a DNS-ish name, so there is no
# legitimate value containing a path separator, a space, or shell metacharacters.
_SAFE_CERTCN = re.compile(r"^[A-Za-z0-9._-]{1,253}$")


async def enroll_peer_product_cert(certcn: str, certpem: str, group: str = "default") -> bool:
    """Write another product's client cert into TAK's cert store and enrol it as a TAK user.

    TAK already trusts anything signed by the RASENMAEHER CA for TLS, but it will reject a
    client whose CN is not a known TAK user. This is what lets a peer product (BattleLog)
    open a CoT stream on 8089. Idempotent: certmod is safe to re-run for an existing cert.

    The group matters as much as the enrolment. certmod puts a user with no group options
    into __ANON__, and CoreConfig sets x509addAnonymous="false", so such a user connects
    and is then dropped every few seconds. That is also why this does not call
    enable_user.sh first: that script is a bare certmod, so it resets a working
    user to __ANON__ on every re-enrolment and depends on a second JVM call to
    put the group back.

    -g sets the in- and out-group together. An out-group alone was the intent -- read
    CoT, cannot publish -- but it leaves __ANON__ as the in-group, which is the
    membership that check rejects, so the connection is dropped exactly as if nothing
    had been set. The peer never writes to the socket, so the in-group is unused.

    Only takrmapi can do this, it needs the tak_data volume and the TAK utils jars.
    """
    if not _SAFE_CERTCN.match(certcn):
        LOGGER.error("Refusing to enrol %r: CN is not a plain DNS-style name", certcn)
        return False
    cert_file = config.TAK_CERTS_FOLDER / f"{certcn}.pem"
    try:
        # x509cert arrives in CFSSL conventions, ie with the newlines escaped
        pem = certpem.replace("\\n", "\n")
        x509.load_pem_x509_certificate(pem.encode("utf-8"))
        cert_file.write_text(pem.rstrip("\n") + "\n", encoding="utf-8")
    except Exception:  # pylint: disable=W0718
        LOGGER.exception("Could not store the certificate for %s", certcn)
        return False
    # One command, deliberately. enable_user.sh runs `certmod` with NO group
    # options, and UserManager documents that as meaning the anonymous group:
    # "If no groups are specified with this or other group options, the user
    # will be added to the anonymous group." So calling it first RESETS an
    # already-correct user to __ANON__, and the group is only restored if the
    # second JVM call also succeeds. Every failure, timeout or restart in
    # between left the peer in __ANON__, which x509addAnonymous="false" then
    # refuses -- the peer enrols "successfully" and is dropped for ever after.
    # certmod adds the user as readily as it modifies one, so the first call
    # bought nothing and cost an outage window on every re-enrolment.
    commands = (
        f"cd /opt/tak && . ./setenv.sh && TAKCL_CORECONFIG_PATH={config.TAKCL_CORECONFIG_PATH}"
        f" java -jar /opt/tak/utils/UserManager.jar certmod -g {shlex.quote(group)} {shlex.quote(str(cert_file))}",
    )
    async with _ENROL_LOCK:
        for cmd in commands:
            try:
                code, _stdout, _stderr = await asyncio.shield(call_cmd(cmd, timeout=JVM_TIMEOUT, stderr_warn=False))
            except TimeoutError:
                LOGGER.error(
                    "Timed out after %ss while enrolling %s, command: %s. The user keeps whatever "
                    "group it already had; raise TAK_RMAPI_JVM_TIMEOUT if this host "
                    "is slow to start a JVM.",
                    JVM_TIMEOUT,
                    certcn,
                    cmd,
                )
                return False
            except asyncio.CancelledError:
                LOGGER.info("Cancellation shielded, just wait")
                return True
            except Exception:  # pylint: disable=W0718
                LOGGER.exception("Could not enrol %s as a TAK user", certcn)
                return False
            if code != 0:
                LOGGER.error("Enrolment step returned %s for %s: %s", code, certcn, cmd)
                return False
    LOGGER.info("Enrolled peer product cert %s as a TAK user reading group %s", certcn, group)
    return True
