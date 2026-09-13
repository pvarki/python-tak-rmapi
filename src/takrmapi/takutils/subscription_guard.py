"""Recheck TLS subscriptions after notifications and periodically from live TAK state."""

from collections.abc import Callable
import logging
from queue import Empty, Full, Queue
import threading
import time
from typing import Protocol

from .revocations import Revocations
from .subscription_jni import Connection, Identity

LOGGER = logging.getLogger(__name__)


class Backend(Protocol):
    """Keep Java and its callback threads outside the enforcement policy."""

    def listen(self, notify: Callable[[Connection], None], failed: Callable[[Exception], None]) -> None: ...
    def snapshot(self) -> list[Connection]: ...
    def identity(self, connection: Connection) -> Identity | None: ...
    def disconnect(self, connection: Connection) -> None: ...
    def close(self) -> None: ...


class SubscriptionGuard:
    """Bounded notification queue; periodic scans also revisit previously valid users."""

    def __init__(
        self,
        backend: Backend,
        revocations: Revocations,
        *,
        require_registered: bool = True,
        interval: float = 5,
        queue_size: int = 4096,
    ) -> None:
        if not 0 < interval <= 30 or queue_size <= 0:
            raise ValueError("Require a scan interval in (0, 30] and a positive queue size")
        self.backend = backend
        self.revocations = revocations
        self.require_registered = require_registered
        self.interval = interval
        self.queue: Queue[Connection] = Queue(maxsize=queue_size)
        self.failures: Queue[Exception] = Queue(maxsize=1)
        self.overflow = threading.Event()

    def notify(self, connection: Connection) -> None:
        """Never block an Ignite callback or call a remote service from it."""
        try:
            self.queue.put_nowait(connection)
        except Full:
            self.overflow.set()

    def failed(self, error: Exception) -> None:
        """Surface callback failures to the supervisor rather than silently losing events."""
        try:
            self.failures.put_nowait(error)
        except Full:
            pass

    def check(self, connection: Connection) -> None:
        """A missing identity is retried by the next notification or live scan."""
        identity = self.backend.identity(connection)
        if identity is None:
            return
        if identity.expires <= time.time():
            reason = "expired"
        elif self.revocations.contains(identity.fingerprint):
            reason = "revoked"
        elif self.require_registered and not identity.registered:
            reason = "unregistered"
        else:
            return
        self.backend.disconnect(connection)
        LOGGER.warning(
            "Disconnected CoT subscription node=%s uid=%s fingerprint=%s reason=%s",
            connection.node,
            connection.uid,
            identity.fingerprint,
            reason,
        )

    def reconcile(self) -> None:
        """Read live subscriptions even if metrics notifications are late or unavailable."""
        self.overflow.clear()
        self.backend.listen(self.notify, self.failed)
        for connection in self.backend.snapshot():
            self.check(connection)

    def run(self, stopping: threading.Event, heartbeat: Callable[[], None]) -> None:
        """Exceptions escape so a fresh process can recover a failed JVM or connection."""
        next_scan = next_prune = 0.0
        try:
            while not stopping.is_set():
                if not self.failures.empty():
                    raise RuntimeError("TAK subscription listener failed") from self.failures.get_nowait()
                now = time.monotonic()
                if now >= next_prune:
                    self.revocations.prune()
                    next_prune = now + 3600
                if now >= next_scan or self.overflow.is_set():
                    self.reconcile()
                    heartbeat()
                    next_scan = time.monotonic() + self.interval
                try:
                    connection = self.queue.get(timeout=min(0.2, max(0, next_scan - time.monotonic())))
                except Empty:
                    continue
                self.check(connection)
        finally:
            self.backend.close()
