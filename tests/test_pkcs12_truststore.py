"""Verify the CA bundles are Java compatible PKCS12 truststores."""

import shutil
import subprocess  # nosec
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from takrmapi.takutils.pkcs12_helpers import (
    load_ca_certificates,
    serialize_java_ca_truststore,
    truststore_alias,
)

KEYTOOL = shutil.which("keytool")


def make_certificate(common_name: str, is_ca: bool = True) -> x509.Certificate:
    """Self-signed certificate with the wanted basic constraints"""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(timezone.utc)
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=is_ca, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )


def pem_bundle(certificates: List[x509.Certificate]) -> bytes:
    """Concatenated PEM bundle"""
    return b"".join(cert.public_bytes(serialization.Encoding.PEM) for cert in certificates)


def java_runtime_works() -> bool:
    """Check we have a usable keytool, the binary alone is not enough on eg macOS"""
    if not KEYTOOL:
        return False
    try:
        return subprocess.run([KEYTOOL, "-help"], capture_output=True, check=False).returncode == 0  # nosec
    except OSError:
        return False


def test_truststore_has_trusted_entries() -> None:
    """The certificates must be exposed as standalone entries, not as a certificate-only blob."""
    certificates = [make_certificate("test CA A"), make_certificate("test CA B")]
    store = pkcs12.load_pkcs12(serialize_java_ca_truststore(certificates, "public"), b"public")
    assert store.key is None
    assert store.cert is None
    assert len(store.additional_certs) == len(certificates)
    assert {entry.friendly_name for entry in store.additional_certs} == {
        truststore_alias(cert) for cert in certificates
    }


def test_certificates_are_deduplicated() -> None:
    """The same CA arriving from two chain sources must not end up twice in the truststore."""
    first = make_certificate("test CA A")
    second = make_certificate("test CA B")
    store = pkcs12.load_pkcs12(serialize_java_ca_truststore([first, second, first], "public"), b"public")
    assert len(store.additional_certs) == 2


def test_aliases_are_deterministic() -> None:
    """Same input, same aliases, so regenerated packages do not churn."""
    certificate = make_certificate("test CA A")
    assert truststore_alias(certificate) == truststore_alias(certificate)
    assert truststore_alias(certificate) != truststore_alias(make_certificate("test CA A"))


def test_empty_truststore_raises() -> None:
    """Never ship a truststore that trusts nothing."""
    with pytest.raises(ValueError):
        serialize_java_ca_truststore([], "public")


def test_leaf_certificates_are_not_loaded() -> None:
    """The HTTPS leaf from the fullchain does not belong in a CA truststore."""
    ca_certificate = make_certificate("test CA A")
    leaf = make_certificate("mtls.example.com", is_ca=False)
    loaded = load_ca_certificates(pem_bundle([ca_certificate, leaf]))
    assert [cert.subject.rfc4514_string() for cert in loaded] == ["CN=test CA A"]


@pytest.mark.skipif(not java_runtime_works(), reason="no usable Java keytool available")
def test_keytool_sees_the_trusted_entries(tmp_path: Path) -> None:
    """OpenSSL parsing the bundle is not enough, ATAK uses Java semantics."""
    assert KEYTOOL
    certificates = [make_certificate("test CFSSL intermediate"), make_certificate("test ISRG Root X1")]
    keystore = tmp_path / "ca-public.p12"
    keystore.write_bytes(serialize_java_ca_truststore(certificates, "public"))
    result = subprocess.run(  # nosec
        [
            KEYTOOL,
            "-list",
            "-v",
            "-storetype",
            "PKCS12",
            "-keystore",
            str(keystore),
            "-storepass",
            "public",
        ],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    assert f"contains {len(certificates)} entries" in result.stdout
    assert result.stdout.count("Entry type: trustedCertEntry") == len(certificates)
