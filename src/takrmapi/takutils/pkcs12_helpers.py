"""PKCS12 helpers, mainly for Java compatible truststores"""

from typing import Iterable, List, Set
import logging

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import PrivateFormat, pkcs12


LOGGER = logging.getLogger(__name__)


def truststore_alias(certificate: x509.Certificate) -> bytes:
    """Stable unique alias for a trusted certificate entry"""
    fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
    return f"cert-{fingerprint[:24]}".encode("ascii")


def is_ca_certificate(certificate: x509.Certificate) -> bool:
    """Check the basic constraints, leaf certificates do not belong in a CA truststore"""
    try:
        constraints = certificate.extensions.get_extension_for_class(x509.BasicConstraints)
    except x509.ExtensionNotFound:
        return False
    return constraints.value.ca


def load_ca_certificates(pemdata: bytes) -> List[x509.Certificate]:
    """Load the CA certificates from a PEM bundle, skipping any leaf certificates"""
    certificates = []
    for certificate in x509.load_pem_x509_certificates(pemdata):
        if not is_ca_certificate(certificate):
            LOGGER.info("Skipping non-CA certificate %s", certificate.subject.rfc4514_string())
            continue
        certificates.append(certificate)
    return certificates


def serialize_java_ca_truststore(certificates: Iterable[x509.Certificate], password: str) -> bytes:
    """Serialize the certificates as a Java compatible PKCS12 truststore.

    Java only exposes trusted certificate entries, a generic certificate-only PKCS12 that OpenSSL
    happily parses shows up as an empty keystore in Java based clients like ATAK.
    """
    unique: List[x509.Certificate] = []
    seen: Set[bytes] = set()
    for certificate in certificates:
        fingerprint = certificate.fingerprint(hashes.SHA256())
        if fingerprint in seen:
            LOGGER.debug("Skipping duplicate certificate %s", certificate.subject.rfc4514_string())
            continue
        seen.add(fingerprint)
        unique.append(certificate)

    if not unique:
        raise ValueError("Cannot create an empty CA truststore")

    entries = [pkcs12.PKCS12Certificate(certificate, truststore_alias(certificate)) for certificate in unique]
    # The truststore holds no private keys, interoperability beats encryption strength here
    encryption = (
        PrivateFormat.PKCS12.encryption_builder()
        .kdf_rounds(50_000)
        .key_cert_algorithm(pkcs12.PBES.PBESv1SHA1And3KeyTripleDESCBC)
        .hmac_hash(hashes.SHA1())  # nosec B303 - no private keys here, old Java clients need this
        .build(password.encode("utf-8"))
    )
    LOGGER.info("Serializing %d trusted certificate entries", len(entries))
    return pkcs12.serialize_java_truststore(entries, encryption)
