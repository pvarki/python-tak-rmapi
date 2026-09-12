"""Revocation decisions survive restarts and concurrent HTTP workers."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from takrmapi.takutils.revocations import Revocations


def certificate(name: str, expires: datetime | None = None) -> tuple[str, str]:
    """A disposable certificate; the store needs its identity and expiry, not a CA."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=2))
        .not_valid_after(expires or now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode(), cert.fingerprint(hashes.SHA256()).hex().upper()


def test_both_identities_survive_restart(tmp_path: Path) -> None:
    path = tmp_path / "revoked.sqlite3"
    identities = [certificate("user"), certificate("user_rm")]
    Revocations(path).record(pem for pem, _ in identities)
    reopened = Revocations(path)
    for _, fingerprint in identities:
        assert reopened.contains(fingerprint.lower())
    replacement = certificate("user")
    assert not reopened.contains(replacement[1])
    assert path.stat().st_mode & 0o777 == 0o600


def test_invalid_batch_is_atomic(tmp_path: Path) -> None:
    store = Revocations(tmp_path / "revoked.sqlite3")
    pem, fingerprint = certificate("user")
    with pytest.raises(ValueError):
        store.record([pem, "invalid certificate"])
    assert not store.contains(fingerprint)


def test_concurrent_writers_do_not_lose_revocations(tmp_path: Path) -> None:
    path = tmp_path / "revoked.sqlite3"
    identities = [certificate(str(index)) for index in range(6)]
    with ThreadPoolExecutor(max_workers=3) as workers:
        list(workers.map(lambda item: Revocations(path).record([item[0]]), identities))
    for _, fingerprint in identities:
        assert Revocations(path).contains(fingerprint)


def test_retry_and_expiry(tmp_path: Path) -> None:
    store = Revocations(tmp_path / "revoked.sqlite3")
    expired = certificate("old", datetime.now(timezone.utc) - timedelta(days=1))
    valid = certificate("current")
    store.record([expired[0], valid[0]])
    store.record([valid[0]])
    store.prune()
    assert not store.contains(expired[1])
    assert store.contains(valid[1])
