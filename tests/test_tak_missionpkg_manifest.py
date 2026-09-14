"""Verify the generated mission package manifests are safe to import into TAK clients."""

import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from jinja2 import Template

from takrmapi import config

CALLSIGN = "RAMBO01"
# Paths the preference files point at, eg cert/enabling-gazelle_rasenmaeher_ca-public.p12
PREF_CERT_RE = re.compile(r">(cert/[^<]+\.p12)<")
ZIPENTRY_RE = re.compile(r'zipEntry="([^"]+)"')
# Only these are known to be consumed by ATAK, see PR156 handoff
ATAK_PACKAGES = ("atak", "atak-mini")
# These clients are not verified for the connection specific soft certificate keys, tak-tracker always had them
GLOBAL_ONLY_PACKAGES = ("itak", "wintak")


@dataclass
class FakeTemplateVars:
    """Just enough of UserTAKTemplateVars to render the templates for any given deployment"""

    deployment: str

    @property
    def tak_userfile_uid(self) -> str:
        """Stable dummy uid"""
        return "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

    @property
    def tak_server_deployment_name(self) -> str:
        """Deployment name mapping"""
        return self.deployment

    @property
    def tak_server_public_address(self) -> str:
        """Public FQDN mapping"""
        return f"tak.{self.deployment}.example.com"

    @property
    def ca_cert_name(self) -> str:
        """CA bundle name mapping, see config.TAK_CA_CERT_NAME"""
        return f"{self.deployment}_rasenmaeher_ca-public"

    @property
    def client_cert_name(self) -> str:
        """Callsign mapping"""
        return CALLSIGN

    @property
    def client_cert_file_name(self) -> str:
        """Users own certificate file name mapping"""
        return f"{self.deployment}_{CALLSIGN}"

    @property
    def client_cert_password(self) -> str:
        """Users own certificate password mapping"""
        return CALLSIGN


def render(template_file: Path, deployment: str) -> str:
    """Render a single template for the given deployment"""
    return Template(template_file.read_text(encoding="utf-8")).render(v=FakeTemplateVars(deployment=deployment))


def render_packages(deployment: str) -> dict[str, dict[str, str]]:
    """Render every mission package for the given deployment, keyed by package and file name"""
    packages: dict[str, dict[str, str]] = {}
    for manifest in sorted(config.TAK_MISSIONPKG_TEMPLATES_FOLDER.rglob("MANIFEST/manifest.xml.tpl")):
        package_folder = manifest.parent.parent
        packages[package_folder.name] = {
            tpl.name[: -len(".tpl")]: render(tpl, deployment) for tpl in sorted(package_folder.rglob("*.tpl"))
        }
    assert packages, "no mission packages found"
    return packages


def zip_entries(manifest: str) -> list[str]:
    """Zip entries in manifest order"""
    return ZIPENTRY_RE.findall(manifest)


def test_certificates_are_listed_before_server_pref() -> None:
    """The client installs the manifest contents in order, certificates must land before server.pref is loaded."""
    for name, files in render_packages("enabling-gazelle").items():
        entries = zip_entries(files["manifest.xml"])
        assert "server.pref" in entries, f"{name} manifest does not ship server.pref"
        prefs_at = entries.index("server.pref")
        ca_at = entries.index("enabling-gazelle_rasenmaeher_ca-public.p12")
        client_at = entries.index(f"enabling-gazelle_{CALLSIGN}.p12")
        assert ca_at < prefs_at, f"{name} installs the CA bundle after server.pref"
        assert client_at < prefs_at, f"{name} installs the users certificate after server.pref"


def test_preference_certificate_paths_are_in_the_manifest() -> None:
    """Every certificate the preferences point at must actually be shipped in the package."""
    for name, files in render_packages("enabling-gazelle").items():
        entries = zip_entries(files["manifest.xml"])
        for filename, content in files.items():
            if not filename.endswith(".pref"):
                continue
            referenced = PREF_CERT_RE.findall(content)
            assert referenced, f"{name}/{filename} references no certificates"
            for path in referenced:
                assert Path(path).name in entries, f"{name}/{filename} references unshipped {path}"


def test_certificate_names_differ_between_deployments() -> None:
    """Packages from two deployments must not overwrite each others files in the shared client cert folder."""
    alpha = render_packages("alpha")
    bravo = render_packages("bravo")
    for name, files in alpha.items():
        alpha_p12s = {entry for entry in zip_entries(files["manifest.xml"]) if entry.endswith(".p12")}
        bravo_p12s = {entry for entry in zip_entries(bravo[name]["manifest.xml"]) if entry.endswith(".p12")}
        assert len(alpha_p12s) == 2, f"{name} does not ship both certificates"
        assert not alpha_p12s & bravo_p12s, f"{name} shares certificate file names between deployments"


def test_no_misspelled_plugin_scanning_preference() -> None:
    """The key is atakPluginScanningOnStartup, the misspelled one is silently ignored by the client."""
    for template in sorted(config.TEMPLATES_PATH.rglob("*")):
        if not template.is_file() or template.suffix not in (".tpl", ".pref", ".rst"):
            continue
        content = template.read_text(encoding="utf-8")
        assert "atakPluginScanninOnStartup" not in content, f"{template} misspells the plugin scanning key"


def pref_entries(content: str, pref_name: str) -> dict[str, str]:
    """Entries of a single named preference block, keyed by preference key"""
    root = ElementTree.fromstring(content)
    for pref in root.findall("preference"):
        if pref.get("name") == pref_name:
            return {entry.get("key", ""): (entry.text or "").strip() for entry in pref.findall("entry")}
    raise AssertionError(f"no '{pref_name}' preference block")


def test_atak_binds_the_certificates_to_the_connection() -> None:
    """ATAK does a host specific CA lookup, the certificates must be bound to the cot_streams entry."""
    packages = render_packages("enabling-gazelle")
    for name in ATAK_PACKAGES:
        streams = pref_entries(packages[name]["server.pref"], "cot_streams")
        assert streams["caLocation0"] == "cert/enabling-gazelle_rasenmaeher_ca-public.p12"
        assert streams["caPassword0"] == "public"  # pragma: allowlist secret
        assert streams["certificateLocation0"] == f"cert/enabling-gazelle_{CALLSIGN}.p12"
        assert streams["clientPassword0"] == CALLSIGN


def test_atak_keeps_the_global_certificate_fields() -> None:
    """The global defaults stay for compatibility until the indexed fields are verified on every ATAK version."""
    packages = render_packages("enabling-gazelle")
    for name in ATAK_PACKAGES:
        prefs = pref_entries(packages[name]["server.pref"], "com.atakmap.app_preferences")
        streams = pref_entries(packages[name]["server.pref"], "cot_streams")
        for key in ("caLocation", "caPassword", "certificateLocation", "clientPassword"):
            assert prefs[key] == streams[f"{key}0"], f"{name} global {key} differs from the connection specific one"


def test_unverified_clients_keep_only_the_global_certificate_fields() -> None:
    """The indexed keys are only verified for ATAK, do not push them to the other clients without testing."""
    packages = render_packages("enabling-gazelle")
    for name in GLOBAL_ONLY_PACKAGES:
        streams = pref_entries(packages[name]["server.pref"], "cot_streams")
        for key in ("caLocation0", "caPassword0", "certificateLocation0", "clientPassword0"):
            assert key not in streams, f"{name} got the unverified connection specific {key}"
