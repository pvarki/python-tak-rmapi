"""Verify the trust anchors shipped to TAK clients."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
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


@pytest.mark.asyncio
async def test_client_trust_bundle_contains_internal_chain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The exported P12 contains exactly the CFSSL intermediate and root, without HTTPS certificates."""
    root_key = ec.generate_private_key(ec.SECP256R1())
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test CFSSL root")])
    now = datetime.now(timezone.utc)
    certificates = []
    for name, key in [
        (root_name, root_key),
        (
            x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test CFSSL intermediate")]),
            ec.generate_private_key(ec.SECP256R1()),
        ),
    ]:
        certificates.append(
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(root_name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(root_key, hashes.SHA256())
        )
    chain_path = tmp_path / "ca_chain.pem"
    chain_path.write_bytes(b"".join(cert.public_bytes(serialization.Encoding.PEM) for cert in reversed(certificates)))
    monkeypatch.setattr(config, "TAK_CA_CHAIN_PATH", chain_path)
    package = TAKPackageZip(Mock(spec=UserCRUD))
    await package.tak_missionpackage_add_p12("<Content>certs/rasenmaeher_ca-public.p12</Content>", tmp_path)
    key, cert, extra = pkcs12.load_key_and_certificates(
        (tmp_path / "certs/rasenmaeher_ca-public.p12").read_bytes(), b"public"
    )
    assert key is None
    actual = ([cert] if cert is not None else []) + extra
    assert len(actual) == 2
    assert {item.fingerprint(hashes.SHA256()) for item in actual} == {
        item.fingerprint(hashes.SHA256()) for item in certificates
    }


@pytest.mark.asyncio
async def test_missing_internal_chain_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never silently fall back to unrelated public CA certificates."""
    monkeypatch.setattr(config, "TAK_CA_CHAIN_PATH", tmp_path / "missing.pem")
    package = TAKPackageZip(Mock(spec=UserCRUD))
    with pytest.raises(FileNotFoundError):
        await package.tak_missionpackage_add_p12("<Content>rasenmaeher_ca-public.p12</Content>", tmp_path)
