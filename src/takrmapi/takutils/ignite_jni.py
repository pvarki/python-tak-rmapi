"""Use Ignite service proxies via PuJNIus"""

from typing import Any, ClassVar, Optional, cast
from pathlib import Path
from dataclasses import dataclass, field
import filelock
import logging

import jnius_config  # type: ignore[import-untyped]

from .. import config

LOGGER = logging.getLogger(__name__)


@dataclass
class TAKCLConfig:
    base_dir: Path = field(
        default=config.TAKCL_CORECONFIG_PATH.parent.parent,
    )
    certs_dir: Path = field(
        default=config.TAK_CERTS_FOLDER,
    )
    cfgfile: Path = field(default=Path("/tmp/TAKCLConfig.xml"))  # nosec
    tmpdir: Path = field(default=Path("/tmp/takcl"))  # nosec
    fb_tmpdir: Path = field(default=Path("/tmp/takcl-fallback"))  # nosec

    def write_takcl_config(self) -> None:
        """Write takcl config XML"""
        # Ensure TMP dirs exist
        LOGGER.debug("Ensuring tmpdirs exist")
        self.tmpdir.mkdir(parents=True, exist_ok=True)
        self.fb_tmpdir.mkdir(parents=True, exist_ok=True)
        # Write the file
        LOGGER.debug("Writing TAKCLConfig.xml")
        self.cfgfile.write_text(
            f"""<?xml version="1.0" encoding="UTF-8"?>
<TAKCLConfiguration xmlns="http://bbn.com/marti/takcl/config" xmlns:c="http://bbn.com/marti/takcl/config/common">
    <c:TemporaryDirectory>{self.tmpdir}</c:TemporaryDirectory>
    <c:FallbackTemporaryDirectory>{self.fb_tmpdir}</c:FallbackTemporaryDirectory>
    <c:RunnableTAKServerConfig
        modelServerDir="{self.base_dir}"
        jarName="takserver-core.jar"
        TAKIgniteConfigFile="data/TAKIgniteConfig.xml"
        serverFarmDir="{self.base_dir}"
        certificateDirectory="{self.certs_dir}"
        certToolDirectory="{self.certs_dir.parent}"
    />
</TAKCLConfiguration>
""".lstrip(),
            encoding="utf-8",
        )


@dataclass
class TAKIgniteOps:
    """Use Ignite service proxies via PuJNIus"""

    ignite_host: str = field(default="127.0.0.1")
    cl_cfg: TAKCLConfig = field(default_factory=TAKCLConfig)

    _profile: Any = field(default=None, init=False)
    _ofa_module: Any = field(default=None, init=False)
    _ssl_helper: Any = field(default=None, init=False)
    _user_manager: Any = field(default=None, init=False)
    _lock: filelock.FileLock = field(default=filelock.FileLock(config.TAK_CERTS_FOLDER / "pjnius_ignite.lock"))
    _singleton: ClassVar[Optional["TAKIgniteOps"]] = None

    @classmethod
    def singleton_teardown(cls) -> None:
        """Handle teardown cleanly even if singleton was not instanced before"""
        if cls._singleton is None:
            LOGGER.info("Singleton was not instantiated, aborting")
            return
        cls._singleton._teardown()
        cls._singleton = None

    @classmethod
    def singleton(cls, **kwargs: Any) -> "TAKIgniteOps":
        """Return singleton"""
        if not TAKIgniteOps._singleton:
            TAKIgniteOps._singleton = TAKIgniteOps(**kwargs)
        return TAKIgniteOps._singleton

    def __post_init__(self) -> None:
        """Whatever more we need"""
        self.init_ignite()

    def init_ignite(self) -> None:
        """Start JVM etc"""
        if self._ofa_module is not None:
            raise RuntimeError("Do not call twice")

        with self._lock.acquire():
            self.cl_cfg.write_takcl_config()
            self._configure_jvm()
            self._load_classes()

    def resolve_cert_username(self, certpath: Path) -> str:
        """Resolve cert username"""
        path_arg = str(certpath.resolve())
        # FIXME: Add error handling
        cert = self._ssl_helper.getCertificate(path_arg)
        return cast(str, self._ssl_helper.getCertificateUserName(cert))

    def add_admin(self, certpath: Path) -> bool:
        """Add cert as admin"""
        # Avoid races
        with self._lock.acquire():
            path_arg = str(certpath.resolve())
            try:
                LOGGER.debug("Calling addAdminCertificates({})".format(path_arg))
                result = self._ofa_module.addAdminCertificates(path_arg)
                LOGGER.debug("result; {}".format(repr(result)))
                if not result:
                    LOGGER.error("Result is falsy: {}".format(repr(result)))
                    return False
                if not isinstance(result, str):
                    LOGGER.error("Result is not string: {}".format(repr(result)))
                    return False
                if not result.endswith("to 'ROLE_ADMIN'."):  # Is this really the best way ?
                    LOGGER.error("Unexpected result: {}".format(repr(result)))
                    return False
                return True
            except Exception as exc:
                LOGGER.exception("JNI addAdminCertificates({}) failed: {}".format(path_arg, exc))
                return False

    def remove_admin(self, path_arg: Path | str) -> bool:
        """Remove admin privileges, underneath works with username so pass that or cert path"""
        if isinstance(path_arg, Path):
            username = self.resolve_cert_username(path_arg)
        else:
            username = path_arg
        # Avoid races
        with self._lock.acquire():
            try:
                result = self._user_manager.setUserRole(username, None)
                LOGGER.debug("result; {}".format(repr(result)))
                if not result:
                    LOGGER.error("Result is falsy: {}".format(repr(result)))
                    return False
                self._user_manager.saveChanges(None)
                return True
            except Exception as exc:
                LOGGER.exception("JNI setUserRole({}, None) failed: {}".format(path_arg, exc))
                return False

    def add_user(self, certpath: Path) -> bool:
        """Add cert as user"""
        # Avoid races
        with self._lock.acquire():
            path_arg = str(certpath.resolve())
            try:
                LOGGER.debug("Calling addCertificates({})".format(path_arg))
                result = self._ofa_module.addCertificates(path_arg)
                LOGGER.debug("result; {}".format(repr(result)))
                if not result:
                    LOGGER.error("Result is falsy: {}".format(repr(result)))
                    return False
                if not isinstance(result, str):
                    LOGGER.error("Result is not string: {}".format(repr(result)))
                    return False
                if not result.endswith("to 'ROLE_ADMIN'."):  # Is this really the best way ?
                    LOGGER.error("Unexpected result: {}".format(repr(result)))
                    return False
                return True
            except Exception as exc:
                LOGGER.exception("JNI addAdminCertificates({}) failed: {}".format(path_arg, exc))
                return False

    def remove_user(self, cert_cn: str | Path) -> bool:
        """Remove user (also removes all privileges)"""
        # FIXME: Should we do what delete_user.sh actually does and set the group to "revoked" instead ?
        #        probably should use the group setting method for that though and leave this as is
        # Avoid races
        with self._lock.acquire():
            if isinstance(cert_cn, Path):
                cert_cn = self.resolve_cert_username(cert_cn)
            try:
                LOGGER.debug("Calling removeUsers({})".format(cert_cn))
                result = self._ofa_module.removeUsers(cert_cn)
                LOGGER.debug("result; {}".format(repr(result)))
                if not result:
                    LOGGER.error("Result is falsy: {}".format(repr(result)))
                    return False
                if not isinstance(result, str):
                    LOGGER.error("Result is not string: {}".format(repr(result)))
                    return False
                if not result.startswith("Removed Users") or cert_cn not in result:  # Is this really the best way ?
                    LOGGER.error("Unexpected result: {}".format(repr(result)))
                    return False
                # TODO: Also kick the users session if removeUsers does not do it
                return True
            except Exception as exc:
                LOGGER.exception("JNI removeUsers({}) failed: {}".format(cert_cn, exc))
                return False

    def _load_classes(self) -> None:
        """Start JVM and load classes"""
        if self._ofa_module is not None:
            raise RuntimeError("Do not call twice")

        # JNI init stuff from LLM: https://chatgpt.com/share/6a8bfe2d-4884-83eb-80d1-326c6d28d9aa
        LOGGER.info("Loading autoclass (starts JVM)")
        # This needs to be imported **after** configuring classpath
        from jnius import autoclass  # type: ignore[import-untyped]

        LOGGER.debug("Loading CLIImmutableServerProfiles")
        CLIProfiles = autoclass("com.bbn.marti.test.shared.data.servers.CLIImmutableServerProfiles")
        LOGGER.debug("Loading MutableServerProfileBuilder")
        MutableServerProfileBuilder = autoclass("com.bbn.marti.test.shared.data.servers.MutableServerProfile$Builder")
        LOGGER.debug("Loading OnlineFileAuthModule")
        OnlineFileAuthModule = autoclass("com.bbn.marti.takcl.AppModules.OnlineFileAuthModule")
        LOGGER.debug("Loading SSLHelper")
        self._ssl_helper = autoclass("com.bbn.marti.takcl.SSLHelper")

        LOGGER.debug("Getting base profile")
        profile_base = CLIProfiles.SERVER_CLI.getServer()
        LOGGER.debug(f"profile_base: {profile_base}")
        LOGGER.debug(f"host: {profile_base.getHost()}")
        LOGGER.debug(f"discovery: {profile_base.getIgniteDiscoveryPort()}")
        LOGGER.debug(f"discovery count: {profile_base.getIgniteDiscoveryPortCount()}")
        LOGGER.debug(f"communication: {profile_base.getIgniteCommunicationPort()}")
        LOGGER.debug(f"communication count: {profile_base.getIgniteCommunicationPortCount()}")

        LOGGER.debug("Creating our profile")
        self._profile = (
            MutableServerProfileBuilder.build(profile_base).setHost(self.ignite_host).setIdentifier("").create()
        )
        LOGGER.debug(f"profile: {self._profile}")
        LOGGER.debug(f"TAK host: {self._profile.getHost()}")
        LOGGER.debug(f"Ignite discovery port: {self._profile.getIgniteDiscoveryPort()}")
        LOGGER.debug(f"Ignite communication port: {self._profile.getIgniteCommunicationPort()}")
        LOGGER.debug(f"Ignite config path: {self._profile.getTAKIgniteConfigFilePath()}")

        LOGGER.debug("Instantiating OnlineFileAuthModule")
        self._ofa_module = OnlineFileAuthModule()

        LOGGER.debug("Instantiating TakclIgniteHelper")
        TakclIgniteHelper = autoclass("com.bbn.marti.takcl.TakclIgniteHelper")

        # FIXME: Handle TAK messaging not being ready for us yet somehow
        LOGGER.info("Initializing {}".format(self._ofa_module))
        self._ofa_module.init(self._profile)
        LOGGER.info("DONE initializing {}".format(self._ofa_module))

        LOGGER.debug("Getting user_manager via TakclIgniteHelper.getUserManager")
        self._user_manager = TakclIgniteHelper.getUserManager(self._profile)

    def _configure_jvm(self) -> None:
        """Apply configs"""
        if self._ofa_module is not None:
            raise RuntimeError("Do not call twice")
        LOGGER.info("Configuring PyJNIus")
        jnius_config.set_classpath(
            "/opt/tak/utils/UserManager.jar",
        )

        # JNI init stuff from LLM: https://chatgpt.com/share/6a8bfe2d-4884-83eb-80d1-326c6d28d9aa
        # Main configutation things
        jnius_config.add_options(
            "-Djava.net.preferIPv4Stack=true",
            "-DIGNITE_UPDATE_NOTIFIER=false",
            "-DIGNITE_QUIET=true",
            f"-Dcom.bbn.marti.takcl.config.filepath={self.cl_cfg.cfgfile}",
            f"-Dio.netty.tmpdir={self.cl_cfg.tmpdir}",
            f"-Djava.io.tmpdir={self.cl_cfg.tmpdir}",
            f"-Dio.netty.native.workdir={self.cl_cfg.tmpdir}",
        )

        # To keep things from exploding
        jnius_config.add_options(
            "--add-opens=java.base/sun.security.pkcs=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.pkcs10=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.util=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.x509=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.tools.keytool=ALL-UNNAMED",
            "--add-opens=java.base/jdk.internal.misc=ALL-UNNAMED",
            "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
            "--add-opens=java.management/com.sun.jmx.mbeanserver=ALL-UNNAMED",
            "--add-opens=jdk.internal.jvmstat/sun.jvmstat.monitor=ALL-UNNAMED",
            "--add-opens=java.base/sun.reflect.generics.reflectiveObjects=ALL-UNNAMED",
            "--add-opens=jdk.management/com.sun.management.internal=ALL-UNNAMED",
            "--add-opens=java.base/java.io=ALL-UNNAMED",
            "--add-opens=java.base/java.nio=ALL-UNNAMED",
            "--add-opens=java.base/java.util=ALL-UNNAMED",
            "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED",
            "--add-opens=java.base/java.util.concurrent.locks=ALL-UNNAMED",
            "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED",
            "--add-opens=java.base/java.lang=ALL-UNNAMED",
            "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED",
            "--add-opens=java.base/java.lang.ref=ALL-UNNAMED",
            "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
            "--add-opens=java.base/java.math=ALL-UNNAMED",
            "--add-opens=java.base/java.net=ALL-UNNAMED",
            "--add-opens=java.sql/java.sql=ALL-UNNAMED",
            "--add-opens=jdk.unsupported/sun.misc=ALL-UNNAMED",
            "--add-opens=java.base/java.security=ALL-UNNAMED",
            "--add-opens=java.base/java.security.cert=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.rsa=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.ssl=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.x500=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.pkcs12=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.provider=ALL-UNNAMED",
            "--add-opens=java.base/javax.security.auth.x500=ALL-UNNAMED",
        )
        LOGGER.info("DONE Configuring PyJNIus")

    def _teardown(self) -> None:
        """Do teardown things"""
        if self._ofa_module is not None:
            LOGGER.info("Halting {}".format(self._ofa_module))
            self._ofa_module.halt()
            LOGGER.info("DONE Halting {}".format(self._ofa_module))
            self._ofa_module = None
