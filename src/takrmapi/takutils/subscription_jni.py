"""TAK subscription notifications and certificate identities through Ignite services."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import logging
from typing import TYPE_CHECKING, Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes

if TYPE_CHECKING:
    from .ignite_jni import TAKIgniteOps

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Connection:
    """Only identifiers assigned by TAK, never client-supplied CoT fields."""

    node: str
    uid: str
    connection_id: str


@dataclass(frozen=True)
class Identity:
    """Certificate authenticated by the TLS connection and its current registration."""

    fingerprint: str
    expires: float
    registered: bool


def connection_from_subscription(sub: Any) -> Connection | None:
    """The initial cache insertion can precede certificate authentication."""
    if not sub.uid.startswith("tls:") or not sub.getConnectionId() or not sub.originNode:
        return None
    return Connection(str(sub.originNode.toString()), str(sub.uid), str(sub.getConnectionId()))


class SubscriptionBackend:
    """All blocking service calls run outside the Java callback under the shared lock."""

    def __init__(self, ops: "TAKIgniteOps") -> None:
        from jnius import autoclass, cast  # type: ignore[import-untyped]

        self.ops = ops
        self.autoclass = autoclass
        self.cast = cast
        self.ignite = cast("org.apache.ignite.Ignite", autoclass("org.apache.ignite.Ignition").allGrids().get(0))
        self.constants = autoclass("tak.server.Constants")
        self.cursor: Any = None
        self.listener: Any = None
        self.proxies: dict[tuple[str, str], Any] = {}

    def _group(self) -> Any:
        return self.autoclass("com.bbn.cluster.ClusterGroupDefinition").getMessagingClusterDeploymentGroup(self.ignite)

    def _service(self, node: str, interface: str, name: str) -> Any:
        key = (node, name)
        if key not in self.proxies:
            cluster = self._group().forNodeId(self.autoclass("java.util.UUID").fromString(node))
            if cluster.nodes().isEmpty():
                raise ConnectionError("TAK messaging node left the cluster")
            loader = self.autoclass("java.lang.ClassLoader").getSystemClassLoader()
            self.proxies[key] = self.cast(
                interface, self.ignite.services(cluster).serviceProxy(name, loader.loadClass(interface), False, 5000)
            )
        return self.proxies[key]

    def _subscriptions(self, node: str) -> Any:
        return self._service(
            node, "com.bbn.marti.remote.SubscriptionManagerLite", self.constants.DISTRIBUTED_SUBSCRIPTION_MANAGER
        )

    def _users(self, node: str) -> Any:
        return self._service(
            node,
            "com.bbn.marti.remote.groups.FileUserManagementInterface",
            self.constants.DISTRIBUTED_USER_FILE_MANAGER,
        )

    def remove_registration(self, username: str) -> bool:
        """Use bounded RPCs instead of TAKCL's unbounded service proxy and text output."""
        with self.ops._lock.acquire(timeout=5):
            nodes = self._group().nodes().toArray()
        if not len(nodes):
            raise ConnectionError("No TAK messaging nodes available")
        results = []
        for node in nodes:
            try:
                with self.ops._lock.acquire(timeout=5):
                    # removeUser also removes privileges and saves the auth file.
                    results.append(self._users(str(node.id().toString())).removeUser(username) is not None)
            except Exception:
                LOGGER.exception("Registration removal failed on TAK node %s", node.id().toString())
                results.append(False)
        return all(results)

    def snapshot(self) -> list[Connection]:
        """Read live services rather than the delayed metrics cache in cluster mode."""
        with self.ops._lock.acquire(timeout=5):
            nodes = self._group().nodes().toArray()
            if not len(nodes):
                raise ConnectionError("No TAK messaging nodes available")
            live = {str(node.id().toString()) for node in nodes}
            self.proxies = {key: proxy for key, proxy in self.proxies.items() if key[0] in live}
            result = []
            for node in live:
                for sub in self._subscriptions(node).getSubscriptionList().toArray():
                    connection = connection_from_subscription(sub)
                    if connection is not None:
                        result.append(connection)
            return result

    def identity(self, connection: Connection) -> Identity | None:
        """Resolve the peer's actual certificate; cache entries deliberately omit it."""
        with self.ops._lock.acquire(timeout=5):
            groups = self._service(
                connection.node, "com.bbn.marti.remote.groups.GroupManager", self.constants.DISTRIBUTED_GROUP_MANAGER
            )
            user = groups.getUserByConnectionId(connection.connection_id)
            if user is None or user.getCert() is None:
                return None
            certificate = x509.load_der_x509_certificate(bytes(user.getCert().getEncoded()))
            fingerprint = certificate.fingerprint(hashes.SHA256()).hex().upper()
            registered = any(
                entry.getFingerprint() and entry.getFingerprint().replace(":", "").upper() == fingerprint
                for entry in self._users(connection.node).getUserAuthenticationFile().getUser().toArray()
            )
            return Identity(fingerprint, certificate.not_valid_after_utc.timestamp(), registered)

    def disconnect(self, connection: Connection) -> None:
        """Select the originating node as subscription UIDs are node-local."""
        with self.ops._lock.acquire(timeout=5):
            if not self._subscriptions(connection.node).deleteSubscription(connection.uid):
                raise RuntimeError("TAK did not acknowledge subscription removal")

    def disconnect_certificate(self, path: Path) -> bool:
        """Immediately close existing sessions on every messaging node."""
        with self.ops._lock.acquire(timeout=5):
            certificate = self.ops._ssl_helper.getCertificate(str(path))
            nodes = self._group().nodes().toArray()
            if not len(nodes):
                raise ConnectionError("No TAK messaging nodes available")
            results = []
            for node in nodes:
                try:
                    results.append(
                        self._subscriptions(str(node.id().toString())).deleteSubscriptionssByCertificate(certificate)
                    )
                except Exception:
                    LOGGER.exception("Certificate disconnect failed on TAK node %s", node.id().toString())
                    results.append(False)
            return all(results)

    def listen(self, notify: Callable[[Connection], None], failed: Callable[[Exception], None]) -> None:
        """Subscribe when TAK creates the cache; reconciliation covers an empty cache."""
        if self.cursor is not None:
            return
        from jnius import PythonJavaClass, java_method

        backend = self

        class Listener(PythonJavaClass):  # type: ignore[misc]
            __javainterfaces__ = ["javax/cache/event/CacheEntryUpdatedListener"]
            __javacontext__ = "app"

            @java_method("(Ljava/lang/Iterable;)V")
            def onUpdated(self, changes: Any) -> None:
                try:
                    iterator = changes.iterator()
                    while iterator.hasNext():
                        event = backend.cast("javax.cache.event.CacheEntryEvent", iterator.next())
                        if event.getEventType().toString() not in ("CREATED", "UPDATED"):
                            continue
                        value = backend.cast("javax.cache.Cache$Entry", event).getValue()
                        if value is not None:
                            connection = connection_from_subscription(
                                backend.cast("com.bbn.marti.remote.RemoteSubscription", value)
                            )
                            if connection is not None:
                                notify(connection)
                except Exception as error:
                    failed(error)

        with self.ops._lock.acquire(timeout=5):
            cache = self.ignite.cache(self.constants.IGNITE_SUBSCRIPTION_UID_TRACKER_CACHE)
            if cache is None:
                return
            self.listener = Listener()
            query = self.autoclass("org.apache.ignite.cache.query.ContinuousQuery")()
            query.setLocalListener(self.listener)
            # Flush from Ignite's timer thread, not the cache-update thread. Sending
            # immediately can hold a server topology lock while retrying a dead
            # watcher and prevent its replacement from joining the cluster.
            query.setPageSize(2**31 - 1)
            query.setTimeInterval(25)
            query.setAutoUnsubscribe(True)
            self.cursor = cache.query(self.cast("org.apache.ignite.cache.query.Query", query))

    def close(self) -> None:
        """Unsubscribe before stopping the JVM; keep the Python callback alive until then."""
        if self.cursor is not None:
            self.cursor.close()
            self.cursor = None
        self.listener = None
