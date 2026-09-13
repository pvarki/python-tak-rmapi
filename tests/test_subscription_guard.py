"""Exercise enforcement without a JVM, including missed events and changing access."""

from pathlib import Path
import threading
import time
from unittest.mock import Mock

import pytest

from takrmapi.takutils.revocations import Revocations
from takrmapi.takutils.subscription_guard import SubscriptionGuard
from takrmapi.takutils.subscription_jni import Connection, Identity

from .test_revocations import certificate

CONNECTION = Connection("node", "tls:1", "connection")


@pytest.mark.parametrize(
    "registered,revoked,expired,required,kicked",
    [
        (True, False, False, True, False),
        (False, False, False, True, True),
        (False, False, False, False, False),
        (True, True, False, True, True),
        (True, True, False, False, True),
        (True, False, True, False, True),
    ],
)
def test_certificate_policy(
    tmp_path: Path, registered: bool, revoked: bool, expired: bool, required: bool, kicked: bool
) -> None:
    pem, fingerprint = certificate("client")
    store = Revocations(tmp_path / "revoked.db")
    if revoked:
        store.record([pem])
    backend = Mock()
    backend.identity.return_value = Identity(fingerprint, time.time() + (-1 if expired else 60), registered)
    SubscriptionGuard(backend, store, require_registered=required).check(CONNECTION)
    assert backend.disconnect.called == kicked


def test_live_scan_retries_missing_identity_and_rechecks_valid_users(tmp_path: Path) -> None:
    backend = Mock()
    backend.snapshot.return_value = [CONNECTION]
    pem, fingerprint = certificate("client")
    identity = Identity(fingerprint, time.time() + 60, True)
    backend.identity.side_effect = [None, identity, identity]
    store = Revocations(tmp_path / "revoked.db")
    guard = SubscriptionGuard(backend, store)
    guard.reconcile()
    guard.reconcile()
    backend.disconnect.assert_not_called()
    store.record([pem])
    guard.reconcile()
    backend.disconnect.assert_called_once_with(CONNECTION)
    assert backend.method_calls[0][0] == "listen"


def test_overflow_reconciles_all_live_connections(tmp_path: Path) -> None:
    backend = Mock()
    backend.snapshot.return_value = [CONNECTION, Connection("node", "tls:2", "second")]
    backend.identity.return_value = Identity("unknown", time.time() + 60, False)
    guard = SubscriptionGuard(backend, Revocations(tmp_path / "revoked.db"), queue_size=1)
    guard.notify(CONNECTION)
    guard.notify(backend.snapshot.return_value[1])
    assert guard.overflow.is_set()
    stopping = threading.Event()
    guard.run(stopping, stopping.set)
    assert backend.disconnect.call_count >= 2
    backend.close.assert_called_once()


def test_listener_failure_is_fatal_and_closes_backend(tmp_path: Path) -> None:
    backend = Mock()
    guard = SubscriptionGuard(backend, Revocations(tmp_path / "revoked.db"))
    guard.failed(ConnectionError("disconnected"))
    with pytest.raises(RuntimeError, match="listener failed"):
        guard.run(threading.Event(), Mock())
    backend.close.assert_called_once()


def test_service_failure_never_reports_healthy(tmp_path: Path) -> None:
    backend = Mock()
    backend.snapshot.side_effect = ConnectionError("messaging unavailable")
    heartbeat = Mock()
    with pytest.raises(ConnectionError):
        SubscriptionGuard(backend, Revocations(tmp_path / "revoked.db")).run(threading.Event(), heartbeat)
    heartbeat.assert_not_called()
    backend.close.assert_called_once()
