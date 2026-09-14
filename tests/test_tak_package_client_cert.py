"""Verify the users own certificate is shipped under a deployment prefixed name."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple
from unittest.mock import AsyncMock, Mock

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from takrmapi import config
from takrmapi.takutils.tak_helpers import UserCRUD
from takrmapi.takutils.tak_pkg_helpers import TAKPackageZip
from takrmapi.takutils.tak_pkg_vars import UserTAKTemplateVars

CALLSIGN = "ROTTA01a"


def make_client_keypair(common_name: str) -> Tuple[str, str]:
    """Self-signed client certificate and its key as PEM strings"""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    keypem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8"), keypem.decode("utf-8")


def mock_user() -> Mock:
    """UserCRUD with just enough to create the P12"""
    certpem, certkey = make_client_keypair(CALLSIGN)
    user = Mock(spec=UserCRUD)
    user.callsign = CALLSIGN
    user.certpem = certpem
    user.certkey = certkey
    user.wait_for_keypair = AsyncMock(return_value=True)
    return user


def test_client_cert_file_name_is_deployment_prefixed() -> None:
    """Packages from different deployments must not fight over the same client certificate file name."""
    template_vars = UserTAKTemplateVars(user=mock_user(), template_file=Path("manifest.xml.tpl"))
    assert template_vars.client_cert_file_name == f"{config.TAK_SERVER_NAME}_{CALLSIGN}"
    # The callsign shown in the client must stay untouched
    assert template_vars.client_cert_name == CALLSIGN
    assert template_vars.client_cert_password == CALLSIGN


def test_missionpkg_templates_use_the_prefixed_client_cert_name() -> None:
    """No mission package template may name the client certificate file by the bare callsign."""
    templates = sorted(config.TAK_MISSIONPKG_TEMPLATES_FOLDER.rglob("*.tpl"))
    assert templates, "no mission package templates found"
    users = [tpl for tpl in templates if "v.client_cert_file_name" in tpl.read_text(encoding="utf-8")]
    assert users, "no template references the client certificate file name variable"
    for tpl in templates:
        content = tpl.read_text(encoding="utf-8")
        assert "v.client_cert_name }}.p12" not in content, f"{tpl} uses the unprefixed client certificate name"


@pytest.mark.asyncio
async def test_client_cert_is_written_under_the_manifest_name(tmp_path: Path) -> None:
    """The P12 lands under the deployment prefixed name the manifest asks for."""
    package = TAKPackageZip(mock_user())
    pkgname = f"{config.TAK_SERVER_NAME}_{CALLSIGN}"
    await package.tak_missionpackage_add_p12('<Content ignore="false" zipEntry="{}.p12"/>'.format(pkgname), tmp_path)
    key, cert, _extra = pkcs12.load_key_and_certificates(
        (tmp_path / f"{pkgname}.p12").read_bytes(), CALLSIGN.encode("utf-8")
    )
    assert key is not None
    assert cert is not None
    assert cert.subject.rfc4514_string() == f"CN={CALLSIGN}"


@pytest.mark.asyncio
async def test_unknown_p12_row_raises(tmp_path: Path) -> None:
    """Never silently skip a certificate the manifest wants."""
    package = TAKPackageZip(mock_user())
    with pytest.raises(RuntimeError):
        await package.tak_missionpackage_add_p12('<Content ignore="false" zipEntry="someoneelse.p12"/>', tmp_path)
