"""Validate server-derived identity handling without starting a host JVM."""

from pathlib import Path
from unittest.mock import MagicMock, Mock

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
