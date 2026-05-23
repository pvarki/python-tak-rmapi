"""Tests for MediaMTX -> TAK sync helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import ssl

import pytest

from takrmapi import config
from takrmapi.takutils import stream_sync as stream_sync_module
from takrmapi.takutils.stream_sync import (
    StreamSyncError,
    MediaMTXTakSync,
    build_interop_request,
    build_video_connection,
    managed_video_uuid,
    plan_video_sync,
)
from takrmapi.takutils.tak_rest_helpers import RestHelpers


def test_build_video_connection() -> None:
    """TAK payload uses JSON uuid fields and RTMPS feed URLs."""
    payload = build_video_connection(
        {
            "path": "/live/demo",
            "alias": "live/demo",
            "urls": {"rtmps": "rtmps://streams.example.test:1936/live/demo?user=user&pass=pass"},
        }
    )
    assert payload["uuid"] == managed_video_uuid("/live/demo")
    assert payload["feeds"][0]["uuid"] == f"{payload['uuid']}-feed0"
    assert payload["feeds"][0]["url"].startswith("rtmps://")


def test_plan_video_sync_create_update_delete() -> None:
    """Diff logic creates, updates, and deletes only managed TAK entries."""
    desired_streams = [
        {
            "path": "/live/demo",
            "alias": "live/demo",
            "urls": {"rtmps": "rtmps://streams.example.test:1936/live/demo?user=user&pass=pass"},
        }
    ]
    existing = [
        {
            "uuid": managed_video_uuid("/live/demo"),
            "active": True,
            "alias": "old-alias",
            "thumbnail": "",
            "classification": config.TAK_VIDEO_CLASSIFICATION,
            "feeds": [
                {
                    "uuid": f"{managed_video_uuid('/live/demo')}-feed0",
                    "active": True,
                    "alias": "old-alias",
                    "url": "rtmps://streams.example.test:1936/live/demo?user=user&pass=pass",
                    "order": 0,
                }
            ],
        },
        {
            "uuid": managed_video_uuid("/live/stale"),
            "active": True,
            "alias": "live/stale",
            "thumbnail": "",
            "classification": config.TAK_VIDEO_CLASSIFICATION,
            "feeds": [],
        },
        {
            "uuid": "manual-video-entry",
            "active": True,
            "alias": "manual",
            "thumbnail": "",
            "classification": config.TAK_VIDEO_CLASSIFICATION,
            "feeds": [],
        },
    ]
    plan = plan_video_sync(desired_streams, existing)
    assert plan.create == []
    assert [item["uuid"] for item in plan.update] == [managed_video_uuid("/live/demo")]
    assert plan.delete == [managed_video_uuid("/live/stale")]


def test_plan_video_sync_noop() -> None:
    """Diff logic is a no-op when TAK already matches desired state."""
    desired_streams = [
        {
            "path": "/live/demo",
            "alias": "live/demo",
            "urls": {"rtmps": "rtmps://streams.example.test:1936/live/demo?user=user&pass=pass"},
        }
    ]
    desired_video = build_video_connection(desired_streams[0])
    plan = plan_video_sync(desired_streams, [desired_video])
    assert plan.create == []
    assert plan.update == []
    assert plan.delete == []


def test_build_interop_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Interop request reads and CFSSL-encodes the product cert."""
    cert_path = tmp_path / "tak.localmaeher.dev.pvarki.fi.pem"
    cert_path.write_text("-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----\n", encoding="utf-8")
    monkeypatch.setattr(config, "RM_PRODUCT_CERT_PATH", cert_path)
    monkeypatch.setattr(config, "read_product_certcn", lambda: "tak.localmaeher.dev.pvarki.fi")
    payload = build_interop_request()
    assert payload["certcn"] == "tak.localmaeher.dev.pvarki.fi"
    assert payload["x509cert"] == "-----BEGIN CERTIFICATE-----\\nabc\\n-----END CERTIFICATE-----\\n"


def test_default_rm_product_paths_fallback_to_mtlsclient(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Default RM product paths reuse the existing mtlsclient files when no CN-named files exist."""
    (tmp_path / "public").mkdir()
    (tmp_path / "private").mkdir()
    cert_path = tmp_path / "public" / "mtlsclient.pem"
    key_path = tmp_path / "private" / "mtlsclient.key"
    cert_path.write_text("cert", encoding="utf-8")
    key_path.write_text("key", encoding="utf-8")
    monkeypatch.setattr(config, "RMAPI_PERSISTENT_FOLDER", tmp_path)
    monkeypatch.setattr(config, "read_product_certcn", lambda: "tak.localmaeher.dev.pvarki.fi")
    assert config.default_rm_product_cert_path() == cert_path
    assert config.default_rm_product_key_path() == key_path


def test_rm_product_ssl_context_requires_ca_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Sync TLS setup fails closed when the local CA directory is unavailable."""
    cert_path = tmp_path / "mtlsclient.pem"
    key_path = tmp_path / "mtlsclient.key"
    cert_path.write_text(
        "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----\n",
        encoding="utf-8",
    )
    key_path.write_text(
        "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "RM_PRODUCT_CERT_PATH", cert_path)
    monkeypatch.setattr(config, "RM_PRODUCT_KEY_PATH", key_path)

    original_is_dir = Path.is_dir

    def fake_is_dir(path: Path) -> bool:
        if path == Path("/ca_public"):
            return False
        return original_is_dir(path)

    monkeypatch.setattr(stream_sync_module.Path, "is_dir", fake_is_dir)

    with pytest.raises(FileNotFoundError, match="RM product CA directory not found"):
        MediaMTXTakSync().rm_product_ssl_context()


@pytest.mark.asyncio
async def test_run_once_executes_tak_mutations() -> None:
    """One sync pass creates missing TAK video connections."""

    class FakeRestHelper:
        def __init__(self) -> None:
            self.created: list[dict[str, Any]] = []
            self.updated: list[tuple[str, dict[str, Any]]] = []
            self.deleted: list[str] = []

        async def tak_api_video_list(self) -> dict[str, Any]:
            return {"success": True, "data": {"videoConnections": []}}

        async def tak_api_video_create(self, payload: dict[str, Any]) -> dict[str, Any]:
            self.created.append(payload)
            return {"success": True, "data": {}}

        async def tak_api_video_update(self, uid: str, payload: dict[str, Any]) -> dict[str, Any]:
            self.updated.append((uid, payload))
            return {"success": True, "data": {}}

        async def tak_api_video_delete(self, uid: str) -> dict[str, Any]:
            self.deleted.append(uid)
            return {"success": True, "data": {}}

    class FakeSync(MediaMTXTakSync):
        async def ensure_interop(self) -> None:
            return None

        async def fetch_authz(self) -> dict[str, Any]:
            return {"type": "basic", "username": "tak.localmaeher.dev.pvarki.fi", "password": "secret"}

        async def fetch_streams(self, authz: dict[str, Any]) -> list[dict[str, Any]]:
            assert authz["username"] == "tak.localmaeher.dev.pvarki.fi"
            return [
                {
                    "path": "/live/demo",
                    "alias": "live/demo",
                    "urls": {"rtmps": "rtmps://streams.example.test:1936/live/demo?user=user&pass=pass"},
                }
            ]

    rest_helper = FakeRestHelper()
    syncer = FakeSync(rest_helper=rest_helper)  # type: ignore[arg-type]
    plan = await syncer.run_once()
    assert len(plan.create) == 1
    assert rest_helper.created == [{"videoConnections": plan.create}]
    assert rest_helper.updated == []
    assert rest_helper.deleted == []


@pytest.mark.asyncio
async def test_run_once_raises_on_create_failure() -> None:
    """Sync fails loudly when TAK create fails."""

    class FakeRestHelper:
        async def tak_api_video_list(self) -> dict[str, Any]:
            return {"success": True, "data": {"videoConnections": []}}

        async def tak_api_video_create(self, payload: dict[str, Any]) -> dict[str, Any]:
            _ = payload
            return {"success": False, "data": {"error": "boom"}}

        async def tak_api_video_update(self, uid: str, payload: dict[str, Any]) -> dict[str, Any]:
            _ = uid
            _ = payload
            raise AssertionError("unexpected update")

        async def tak_api_video_delete(self, uid: str) -> dict[str, Any]:
            _ = uid
            raise AssertionError("unexpected delete")

    class FakeSync(MediaMTXTakSync):
        async def ensure_interop(self) -> None:
            return None

        async def fetch_authz(self) -> dict[str, Any]:
            return {"type": "basic", "username": "tak.localmaeher.dev.pvarki.fi", "password": "secret"}

        async def fetch_streams(self, authz: dict[str, Any]) -> list[dict[str, Any]]:
            assert authz["username"] == "tak.localmaeher.dev.pvarki.fi"
            return [
                {
                    "path": "/live/demo",
                    "alias": "live/demo",
                    "urls": {"rtmps": "rtmps://streams.example.test:1936/live/demo?user=user&pass=pass"},
                }
            ]

    with pytest.raises(StreamSyncError, match="Unable to create TAK video connections"):
        await FakeSync(rest_helper=FakeRestHelper()).run_once()  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_tak_video_rest_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    """TAK video helpers hit the documented endpoints and payload shapes."""

    class FakeResponse:
        def __init__(self, status: int, payload: dict[str, Any] | None = None) -> None:
            self.status = status
            self._payload = payload or {}

        async def json(self, content_type: str | None = None) -> dict[str, Any]:
            _ = content_type
            return self._payload

        async def text(self) -> str:
            return ""

    class FakeSession:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

        async def __aenter__(self) -> "FakeSession":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            _ = exc_type
            _ = exc
            _ = tb

        async def get(self, url: str, ssl: ssl.SSLContext | None = None) -> FakeResponse:
            _ = ssl
            self.calls.append(("get", url, None))
            return FakeResponse(200, {"videoConnections": []})

        async def post(self, url: str, json: dict[str, Any], ssl: ssl.SSLContext | None = None) -> FakeResponse:
            _ = ssl
            self.calls.append(("post", url, json))
            return FakeResponse(201, {})

        async def put(self, url: str, json: dict[str, Any], ssl: ssl.SSLContext | None = None) -> FakeResponse:
            _ = ssl
            self.calls.append(("put", url, json))
            return FakeResponse(200, {})

        async def delete(self, url: str, ssl: ssl.SSLContext | None = None) -> FakeResponse:
            _ = ssl
            self.calls.append(("delete", url, None))
            return FakeResponse(200, {})

    helper = RestHelpers()
    session = FakeSession()

    async def fake_tak_mtls_client() -> FakeSession:
        return session

    async def fake_tak_mtls_client_sslcontext() -> None:
        return None

    monkeypatch.setattr(helper.helpers, "tak_mtls_client", fake_tak_mtls_client)
    monkeypatch.setattr(helper.helpers, "tak_mtls_client_sslcontext", fake_tak_mtls_client_sslcontext)
    monkeypatch.setattr(helper.helpers, "tak_base_url", lambda: "https://tak.example.test:8443")

    create_payload = {"videoConnections": [{"uuid": "demo"}]}
    update_payload = {"uuid": "demo", "feeds": []}
    list_resp = await helper.tak_api_video_list()
    create_resp = await helper.tak_api_video_create(create_payload)
    update_resp = await helper.tak_api_video_update("demo", update_payload)
    delete_resp = await helper.tak_api_video_delete("demo")

    assert list_resp["success"] is True
    assert create_resp["success"] is True
    assert update_resp["success"] is True
    assert delete_resp["success"] is True
    assert session.calls == [
        ("get", "https://tak.example.test:8443/Marti/api/video", None),
        ("post", "https://tak.example.test:8443/Marti/api/video", create_payload),
        ("put", "https://tak.example.test:8443/Marti/api/video/demo", update_payload),
        ("delete", "https://tak.example.test:8443/Marti/api/video/demo", None),
    ]
