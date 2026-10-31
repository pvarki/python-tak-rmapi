"""Validate federation inputs before networking or TAK mutations."""

from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from takrmapi.api.federation_schemas import FederationRequest
from takrmapi.takutils.federation import MAX_CA_BYTES, intermediate_fingerprint


@pytest.fixture
def ca_pem() -> bytes:
    """A current intermediate, signed by a test CA key."""
    return make_cert()


def make_cert(*, ca: bool = True, root: bool = False, days: int = 1, key_sign: bool = True) -> bytes:
    """Small certificate fixture with selectable rejection cases."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "remote")])
    issuer = subject if root else x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "root")])
    now = datetime.now(UTC)
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=2))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(False, False, False, False, False, key_sign, False, False, False), critical=True)
        .sign(key, hashes.SHA256())
        .public_bytes(serialization.Encoding.PEM)
    )


@pytest.mark.parametrize(
    "value",
    [
        "https://remote.example",
        "tak.remote.example",
        "remote.example/",
        "u@remote.example",
        "remote.example?a",
        "127.0.0.1",
        "[::1]",
        "remote",
        "a..example",
        "-a.example",
        "a_.example",
        "a.example:0",
        "a.example:65536",
        "a.example:",
        "a" * 31 + ".example",
        "a.example\n",
    ],
)
def test_bad_peer(value: str) -> None:
    with pytest.raises(ValueError):
        FederationRequest(remote_base=value)


def test_peer() -> None:
    peer = FederationRequest(remote_base="FAST-Flounder.other.example:0443")
    assert peer.remote_base == "fast-flounder.other.example"
    assert peer.hostname == "fast-flounder.other.example"
    assert peer.display_name == "fast_flounder"
    assert FederationRequest(remote_base="remote.example:4439").remote_base == "remote.example:4439"
    with pytest.raises(ValueError):
        FederationRequest(remote_base="remote.example", port=9001)


def test_fingerprint(ca_pem: bytes) -> None:
    expected = x509.load_pem_x509_certificate(ca_pem).fingerprint(hashes.SHA256()).hex(":").upper()
    assert intermediate_fingerprint(ca_pem) == expected
    for invalid in (b"garbage", ca_pem + ca_pem, b"x" * MAX_CA_BYTES, ca_pem + b"extra"):
        with pytest.raises(ValueError):
            intermediate_fingerprint(invalid)


@pytest.mark.parametrize("kwargs", [{"ca": False}, {"root": True}, {"days": -1}, {"key_sign": False}])
def test_invalid_ca(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        intermediate_fingerprint(make_cert(**kwargs))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,body",
    [(200, b"pem"), (302, b"redirect"), (200, b"x" * MAX_CA_BYTES)],
    ids=["valid", "redirect", "oversize"],
)
async def test_download_policy(monkeypatch: pytest.MonkeyPatch, status: int, body: bytes) -> None:
    """No redirects or client identity, and cap the streamed, decoded body."""
    import ssl
    from unittest.mock import AsyncMock, MagicMock

    import aiohttp

    from takrmapi.takutils.federation import download_intermediate

    async def chunks(size: int):
        for offset in range(0, len(body), size):
            yield body[offset : offset + size]

    response = MagicMock(status=status)
    response.content.iter_chunked = chunks
    context = AsyncMock()
    context.__aenter__.return_value = response
    session = MagicMock()
    session.get.return_value = context
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr("takrmapi.takutils.federation.aiohttp.ClientSession", factory)
    if status == 200 and len(body) < MAX_CA_BYTES:
        assert await download_intermediate("remote.example:4439") == body
    else:
        with pytest.raises(ValueError):
            await download_intermediate("remote.example:4439")
    options = factory.call_args.kwargs
    assert isinstance(options["cookie_jar"], aiohttp.DummyCookieJar)
    assert options["trust_env"] is False
    args, kwargs = session.get.call_args
    assert args == ("https://remote.example:4439/ca/public/intermediate_ca.pem",)
    assert kwargs["allow_redirects"] is False
    assert kwargs["ssl"].verify_mode == ssl.CERT_REQUIRED
    assert kwargs["ssl"].check_hostname
    assert "cert" not in kwargs and "headers" not in kwargs
