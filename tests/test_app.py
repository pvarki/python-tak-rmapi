"""Tests for takrmapi application lifecycle."""

from __future__ import annotations

from pathlib import Path
import asyncio

import pytest
from fastapi import FastAPI

from takrmapi import app as app_module


@pytest.mark.asyncio
async def test_sync_worker_runs_only_once_across_workers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only one overlapping worker lifespan may start the periodic sync loop."""

    class FakeLock:
        held_paths: dict[Path, bool] = {}

        def __init__(self, lock_file: Path) -> None:
            self.lock_file = lock_file

        def acquire(self, timeout: float = -1) -> None:
            _ = timeout
            if FakeLock.held_paths.get(self.lock_file, False):
                raise app_module.filelock.Timeout(str(self.lock_file))
            FakeLock.held_paths[self.lock_file] = True

        def release(self) -> None:
            if not FakeLock.held_paths.get(self.lock_file, False):
                raise RuntimeError(f"Attempted to release unlocked lock {self.lock_file}")
            FakeLock.held_paths[self.lock_file] = False

        @property
        def is_locked(self) -> bool:
            return FakeLock.held_paths.get(self.lock_file, False)

    started = 0
    stop_event = asyncio.Event()

    async def fake_setup() -> None:
        return None

    async def fake_get_defaults() -> None:
        return None

    async def fake_run_forever(self) -> None:
        nonlocal started
        _ = self
        started += 1
        await stop_event.wait()

    monkeypatch.setattr(app_module.filelock, "FileLock", FakeLock)
    monkeypatch.setattr(app_module.random, "random", lambda: 0.0)
    monkeypatch.setattr(app_module.config, "TAK_CERTS_FOLDER", tmp_path)
    monkeypatch.setattr(app_module.config, "STREAM_SYNC_ENABLED", True)
    monkeypatch.setattr(app_module.tak_init, "setup_tak_mgmt_conn", fake_setup)
    monkeypatch.setattr(app_module.tak_init, "setup_tak_defaults", fake_setup)
    monkeypatch.setattr(app_module.tak_init, "get_tak_defaults", fake_get_defaults)
    monkeypatch.setattr(app_module.MediaMTXTakSync, "run_forever", fake_run_forever)

    async with app_module.app_lifespan(FastAPI()):
        async with app_module.app_lifespan(FastAPI()):
            await asyncio.sleep(0)
            assert started == 1
