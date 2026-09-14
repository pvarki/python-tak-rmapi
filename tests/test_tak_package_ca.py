"""Verify the trust anchors shipped to TAK clients."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List
from unittest.mock import Mock

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from takrmapi import config
from takrmapi.takutils.tak_helpers import UserCRUD
from takrmapi.takutils.tak_pkg_helpers import TAKPackageZip


def make_ca_chain(common_names: List[str]) -> List[x509.Certificate]:
    """Self-signed root plus intermediates signed by it, root first"""
    root_key = ec.generate_private_key(ec.SECP256R1())
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_names[0])])
    now = datetime.now(timezone.utc)
    certificates = []
    for common_name in common_names:
        key = root_key if common_name == common_names[0] else ec.generate_private_key(ec.SECP256R1())
        certificates.append(
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
            .issuer_name(root_name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(root_key, hashes.SHA256())
        )
    return certificates


def write_chain(target: Path, certificates: List[x509.Certificate]) -> Path:
    """Write the certificates as a leaf-first PEM chain"""
    target.write_bytes(b"".join(cert.public_bytes(serialization.Encoding.PEM) for cert in reversed(certificates)))
    return target


@pytest.mark.asyncio
async def test_client_trust_bundle_contains_all_anchors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The exported P12 contains the CFSSL chain, the HTTPS chain and the bundled public roots."""
    internal = make_ca_chain(["test CFSSL root", "test CFSSL intermediate"])
    https = make_ca_chain(["test LE root", "test LE intermediate"])
    monkeypatch.setattr(config, "TAK_CA_CHAIN_PATH", write_chain(tmp_path / "ca_chain.pem", internal))
    monkeypatch.setattr(config, "TAK_LE_CHAIN_PATH", write_chain(tmp_path / "fullchain.pem", https))
    package = TAKPackageZip(Mock(spec=UserCRUD))
    await package.tak_missionpackage_add_p12("<Content>certs/rasenmaeher_ca-public.p12</Content>", tmp_path)
    key, cert, extra = pkcs12.load_key_and_certificates(
        (tmp_path / "certs/rasenmaeher_ca-public.p12").read_bytes(), b"public"
    )
    assert key is None
    actual = ([cert] if cert is not None else []) + extra
    bundled = [
        x509.load_pem_x509_certificate(pem_file.read_bytes())
        for pem_file in sorted(config.TEMPLATES_PATH.rglob("*.pem"))
    ]
    assert bundled, "no PEM trust anchors are shipped with the package"
    expected = internal + https + bundled
    assert len(actual) == len(expected)
    assert {item.fingerprint(hashes.SHA256()) for item in actual} == {
        item.fingerprint(hashes.SHA256()) for item in expected
    }


@pytest.mark.asyncio
async def test_isrg_root_is_shipped() -> None:
    """The Let's Encrypt root must stay in the templates so clients trust the HTTPS endpoints."""
    isrg = x509.load_pem_x509_certificate((config.TEMPLATES_PATH / "1_isrg-x1.pem").read_bytes())
    assert isrg.subject.rfc4514_string() == "CN=ISRG Root X1,O=Internet Security Research Group,C=US"


@pytest.mark.asyncio
async def test_missing_internal_chain_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never silently ship a bundle without the internal CA."""
    monkeypatch.setattr(config, "TAK_CA_CHAIN_PATH", tmp_path / "missing.pem")
    package = TAKPackageZip(Mock(spec=UserCRUD))
    with pytest.raises(FileNotFoundError):
        await package.tak_missionpackage_add_p12("<Content>rasenmaeher_ca-public.p12</Content>", tmp_path)


@pytest.mark.asyncio
async def test_missing_https_chain_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never silently ship a bundle without the HTTPS chain."""
    internal = make_ca_chain(["test CFSSL root", "test CFSSL intermediate"])
    monkeypatch.setattr(config, "TAK_CA_CHAIN_PATH", write_chain(tmp_path / "ca_chain.pem", internal))
    monkeypatch.setattr(config, "TAK_LE_CHAIN_PATH", tmp_path / "missing.pem")
    package = TAKPackageZip(Mock(spec=UserCRUD))
    with pytest.raises(FileNotFoundError):
        await package.tak_missionpackage_add_p12("<Content>rasenmaeher_ca-public.p12</Content>", tmp_path)
