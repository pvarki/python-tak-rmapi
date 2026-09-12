"""Persist certificate revocations independently of OCSP and TAK registrations."""

from collections.abc import Iterable
from contextlib import closing
from pathlib import Path
import sqlite3
import time

from cryptography import x509
from cryptography.hazmat.primitives import hashes

from takrmapi import config


class Revocations:
    """Atomic, process-safe denylist for both of a user's certificate identities."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else config.RMAPI_PERSISTENT_FOLDER / "revocations.sqlite3"

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS revoked (fingerprint TEXT PRIMARY KEY, expires REAL NOT NULL)"
            )
            self.path.chmod(0o600)
        except BaseException:
            connection.close()
            raise
        return connection

    def record(self, certificates: Iterable[str]) -> None:
        """Validate every PEM before durably recording the batch in one transaction."""
        rows = []
        for pem in certificates:
            cert = x509.load_pem_x509_certificate(pem.encode("utf-8"))
            rows.append((cert.fingerprint(hashes.SHA256()).hex().upper(), cert.not_valid_after_utc.timestamp()))
        if not rows:
            raise ValueError("No certificates supplied for revocation")
        with closing(self._connect()) as connection, connection:
            connection.executemany(
                "INSERT INTO revoked VALUES (?, ?) ON CONFLICT(fingerprint) "
                "DO UPDATE SET expires = MAX(revoked.expires, excluded.expires)",
                rows,
            )

    def contains(self, fingerprint: str) -> bool:
        """Never depend on OCSP freshness or a possibly stale registration cache."""
        with closing(self._connect()) as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM revoked WHERE fingerprint = ?", (fingerprint.replace(":", "").upper(),)
                ).fetchone()
                is not None
            )

    def prune(self, now: float | None = None) -> None:
        """Expired certificates are rejected by TAK itself, including after resumption."""
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM revoked WHERE expires < ?", (time.time() if now is None else now,))
