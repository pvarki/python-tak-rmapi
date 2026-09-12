"""Supervise HTTP workers and an independently restartable JNI subscription watcher."""

from collections.abc import Iterator
from contextlib import contextmanager
import logging
import os
from pathlib import Path
import signal
import subprocess  # nosec B404
import sys
import threading
import time
from types import FrameType

from filelock import FileLock

from takrmapi import config

LOGGER = logging.getLogger(__name__)
HEARTBEAT_TIMEOUT = 60.0
STARTUP_TIMEOUT = 180.0


def guard_healthy() -> bool:
    """A recent completed live scan is required, not merely a running watcher PID."""
    try:
        age = time.time() - config.SUBSCRIPTION_GUARD_HEARTBEAT.stat().st_mtime
        return 0 <= age < HEARTBEAT_TIMEOUT
    except OSError:
        return False


def heartbeat() -> None:
    """The directory belongs to this container; only the singleton watcher writes here."""
    path = config.SUBSCRIPTION_GUARD_HEARTBEAT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600)


@contextmanager
def stop_signals() -> Iterator[threading.Event]:
    """Give HTTP and JNI shutdown a deadline even when Java cannot return."""
    stopping = threading.Event()

    def stop(_signum: int, _frame: FrameType | None) -> None:
        stopping.set()

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        yield stopping
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def watch_subscriptions() -> None:
    """Run exactly one watcher per shared persistent volume in a fresh JVM."""
    from takrmapi.takutils.ignite_jni import TAKIgniteOps
    from takrmapi.takutils.revocations import Revocations
    from takrmapi.takutils.subscription_guard import SubscriptionGuard
    from takrmapi.takutils.subscription_jni import SubscriptionBackend

    config.RMAPI_PERSISTENT_FOLDER.mkdir(parents=True, exist_ok=True)
    with FileLock(config.RMAPI_PERSISTENT_FOLDER / "subscriptions.lock", timeout=0), stop_signals() as stopping:
        config.SUBSCRIPTION_GUARD_HEARTBEAT.unlink(missing_ok=True)
        try:
            backend = SubscriptionBackend(TAKIgniteOps.singleton())
            SubscriptionGuard(
                backend,
                Revocations(),
                require_registered=config.SUBSCRIPTION_GUARD_REQUIRE_REGISTERED,
                interval=config.SUBSCRIPTION_GUARD_INTERVAL,
            ).run(stopping, heartbeat)
        finally:
            config.SUBSCRIPTION_GUARD_HEARTBEAT.unlink(missing_ok=True)
            TAKIgniteOps.singleton_teardown()


def terminate(process: subprocess.Popen[bytes]) -> None:
    """Stop the whole child process group, including Gunicorn workers."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait()
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    # Also reap descendants if the process leader exited before its workers.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def serve() -> int:
    """Keep the HTTP API available for revocations while recovering the watcher."""
    command = [
        str(Path(sys.executable).with_name("gunicorn")),
        "takrmapi.app:get_app()",
        "--bind",
        "0.0.0.0:8003",
        "--forwarded-allow-ips=*",
        "-w",
        "2",
        "-k",
        "uvicorn.workers.UvicornWorker",
    ]
    watcher: subprocess.Popen[bytes] | None = None
    next_start = started = 0.0
    failures = 0
    with stop_signals() as stopping:
        config.SUBSCRIPTION_GUARD_HEARTBEAT.unlink(missing_ok=True)
        # Executable and arguments are fixed; no shell or request input is used.
        http = subprocess.Popen(command, start_new_session=True)  # nosec B603
        try:
            while not stopping.wait(0.5):
                if http.poll() is not None:
                    return http.returncode or 1
                if not config.SUBSCRIPTION_GUARD_ENABLED:
                    continue
                now = time.monotonic()
                if watcher is None and now >= next_start:
                    config.SUBSCRIPTION_GUARD_HEARTBEAT.unlink(missing_ok=True)
                    watcher = subprocess.Popen(  # nosec B603
                        [str(Path(sys.executable).with_name("takrmapi")), "watch-subscriptions"],
                        start_new_session=True,
                    )
                    started = now
                    LOGGER.warning("Started subscription watcher pid=%s", watcher.pid)
                if watcher is None:
                    continue
                stale = now - started > STARTUP_TIMEOUT and not guard_healthy()
                if watcher.poll() is not None or stale:
                    LOGGER.error("Restarting subscription watcher pid=%s stale=%s", watcher.pid, stale)
                    config.SUBSCRIPTION_GUARD_HEARTBEAT.unlink(missing_ok=True)
                    terminate(watcher)
                    watcher = None
                    failures = 1 if now - started > STARTUP_TIMEOUT else min(failures + 1, 5)
                    next_start = time.monotonic() + min(2**failures, 30)
        finally:
            config.SUBSCRIPTION_GUARD_HEARTBEAT.unlink(missing_ok=True)
            if watcher is not None:
                terminate(watcher)
            terminate(http)
    return 0
