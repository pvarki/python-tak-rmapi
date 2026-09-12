"""Validate server-derived identity handling without starting a host JVM."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from takrmapi.takutils.ignite_jni import TAKIgniteOps

from takrmapi.takutils.subscription_jni import Connection, SubscriptionBackend, connection_from_subscription


def test_initial_subscription_without_identity_is_deferred() -> None:
    sub = Mock(uid="tls:1")
    sub.getConnectionId.return_value = None
    assert connection_from_subscription(sub) is None
    sub.getConnectionId.return_value = "server-connection"
    sub.originNode.toString.return_value = "server-node"
    assert connection_from_subscription(sub) == Connection("server-node", "tls:1", "server-connection")
    sub.uid = "websocket:1"
    assert connection_from_subscription(sub) is None


def test_disconnect_attempts_every_messaging_node_on_failure() -> None:
    backend = MagicMock()
    backend.ops._lock = MagicMock()
    nodes = [Mock(), Mock()]
    for index, node in enumerate(nodes):
        node.id.return_value.toString.return_value = str(index)
    backend._group.return_value.nodes.return_value.toArray.return_value = nodes
    services = [Mock(), Mock()]
    services[0].deleteSubscriptionssByCertificate.side_effect = ConnectionError("first node unavailable")
    services[1].deleteSubscriptionssByCertificate.return_value = True
    backend._subscriptions.side_effect = services
    assert not SubscriptionBackend.disconnect_certificate(backend, Path("user.pem"))
    services[1].deleteSubscriptionssByCertificate.assert_called_once_with(
        backend.ops._ssl_helper.getCertificate.return_value
    )


def test_registration_removal_attempts_remaining_nodes_after_timeout() -> None:
    backend = MagicMock()
    backend.ops._lock = MagicMock()
    nodes = [Mock(), Mock()]
    for index, node in enumerate(nodes):
        node.id.return_value.toString.return_value = str(index)
    backend._group.return_value.nodes.return_value.toArray.return_value = nodes
    services = [Mock(), Mock()]
    services[0].removeUser.side_effect = TimeoutError("auth file update timed out")
    backend._users.side_effect = services
    assert not SubscriptionBackend.remove_registration(backend, "test")
    services[1].removeUser.assert_called_once_with("test")


@pytest.mark.parametrize("raises", [False, True])
def test_disconnect_still_attempted_when_registration_removal_fails(raises: bool) -> None:
    ops = MagicMock()
    ops._lock = MagicMock()
    ops.resolve_cert_username.return_value = "test"
    backend = Mock()
    backend.remove_registration.return_value = False
    if raises:
        backend.remove_registration.side_effect = TimeoutError("service unavailable")
    with patch("takrmapi.takutils.subscription_jni.SubscriptionBackend", return_value=backend):
        assert not TAKIgniteOps.remove_user(ops, Path("test.pem"))
    ops.disconnect_user.assert_called_once_with(Path("test.pem"))
