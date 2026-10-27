"""Federation operations through TAK's REST controller and Ignite services."""

import re
import ssl
from datetime import UTC, datetime

import aiohttp
from cryptography import x509
from cryptography.hazmat.primitives import hashes

MAX_CA_BYTES = 1024 * 1024


def intermediate_fingerprint(pem: bytes) -> str:
    """Require exactly one current intermediate CA before any TAK mutation."""
    if len(pem) >= MAX_CA_BYTES or not re.fullmatch(
        rb"\s*-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----\s*", pem
    ):
        raise ValueError("Expected exactly one PEM certificate smaller than 1 MiB")
    cert = x509.load_pem_x509_certificate(pem)
    now = datetime.now(UTC)
    if not cert.not_valid_before_utc <= now < cert.not_valid_after_utc:
        raise ValueError("CA certificate is not currently valid")
    if cert.subject == cert.issuer:
        raise ValueError("Expected an intermediate CA, not a root")
    try:
        if not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise ValueError("Certificate is not a CA")
    except x509.ExtensionNotFound as exc:
        raise ValueError("Missing CA basic constraints") from exc
    try:
        if not cert.extensions.get_extension_for_class(x509.KeyUsage).value.key_cert_sign:
            raise ValueError("CA key usage does not permit certificate signing")
    except x509.ExtensionNotFound:
        pass
    return cert.fingerprint(hashes.SHA256()).hex(":").upper()


async def download_intermediate(remote_base: str) -> bytes:
    """Use public HTTPS trust without local credentials, cookies or redirects."""
    async with (
        aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5), cookie_jar=aiohttp.DummyCookieJar(), trust_env=False
        ) as session,
        session.get(
            f"https://{remote_base}/ca/public/intermediate_ca.pem",
            ssl=ssl.create_default_context(),
            allow_redirects=False,
        ) as response,
    ):
        if response.status != 200:
            raise ValueError("Remote CA download did not return HTTP 200")
        pem = bytearray()
        async for chunk in response.content.iter_chunked(65536):
            pem.extend(chunk)
            if len(pem) >= MAX_CA_BYTES:
                raise ValueError("Remote CA certificate exceeds size limit")
        return bytes(pem)
