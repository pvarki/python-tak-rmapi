"""Watcher liveness and child lifecycle behavior."""

import os
from pathlib import Path
import signal
import subprocess
import time
from unittest.mock import Mock, patch

from takrmapi import config
from takrmapi.runtime import HEARTBEAT_TIMEOUT, guard_healthy, heartbeat, serve, terminate


def test_health_requires_a_recent_completed_scan(tmp_path: Path) -> None:
    with patch.object(config, "SUBSCRIPTION_GUARD_HEARTBEAT", tmp_path / "run" / "heartbeat"):
        assert not guard_healthy()
        heartbeat()
        assert guard_healthy()
        stale = time.time() - HEARTBEAT_TIMEOUT - 1
        os.utime(config.SUBSCRIPTION_GUARD_HEARTBEAT, (stale, stale))
        assert not guard_healthy()


def test_terminate_kills_a_child_that_ignores_sigterm() -> None:
    process = Mock()
    process.pid = 12345
    process.wait.side_effect = [subprocess.TimeoutExpired("watcher", 10), 0]
    with patch("takrmapi.runtime.os.killpg") as kill:
        terminate(process)
    assert [call.args for call in kill.call_args_list] == [(12345, signal.SIGTERM), (12345, signal.SIGKILL)]


def test_supervisor_restarts_exited_watcher_and_stops_children(tmp_path: Path) -> None:
    stopping = Mock()
    stopping.wait.side_effect = [False, False, False, True]
    http, first, replacement = Mock(), Mock(), Mock()
    http.poll.return_value = replacement.poll.return_value = None
    first.poll.side_effect = [None, 1]
    with (
        patch.object(config, "SUBSCRIPTION_GUARD_HEARTBEAT", tmp_path / "heartbeat"),
        patch.object(config, "SUBSCRIPTION_GUARD_ENABLED", True),
        patch("takrmapi.runtime.stop_signals") as signals,
        patch("takrmapi.runtime.time.monotonic", side_effect=[10, 11, 11, 20]),
        patch("takrmapi.runtime.subprocess.Popen", side_effect=[http, first, replacement]) as spawn,
        patch("takrmapi.runtime.terminate") as stop,
    ):
        signals.return_value.__enter__.return_value = stopping
        assert serve() == 0
    assert spawn.call_count == 3
    assert [call.args[0] for call in stop.call_args_list] == [first, replacement, http]


def test_supervisor_restarts_a_stalled_jvm(tmp_path: Path) -> None:
    stopping = Mock()
    stopping.wait.side_effect = [False, False, True]
    http, watcher = Mock(), Mock()
    http.poll.return_value = watcher.poll.return_value = None
    with (
        patch.object(config, "SUBSCRIPTION_GUARD_HEARTBEAT", tmp_path / "heartbeat"),
        patch.object(config, "SUBSCRIPTION_GUARD_ENABLED", True),
        patch("takrmapi.runtime.stop_signals") as signals,
        patch("takrmapi.runtime.time.monotonic", side_effect=[10, 200, 200]),
        patch("takrmapi.runtime.subprocess.Popen", side_effect=[http, watcher]),
        patch("takrmapi.runtime.terminate") as stop,
    ):
        signals.return_value.__enter__.return_value = stopping
        assert serve() == 0
    assert [call.args[0] for call in stop.call_args_list] == [watcher, http]
