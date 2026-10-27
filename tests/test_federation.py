"""Retryable federation changes and their internal authorization boundary."""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock
from urllib.parse import unquote

import aiohttp
import filelock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from takrmapi import config
from takrmapi.api.federation_schemas import FederationRequest
from takrmapi.takutils import federation
from takrmapi.takutils.tak_rest_helpers import RestHelpers

from .test_federation_validation import make_cert

PEER = "fast-flounder.other.example"


class FakeTAK:
    """Stateful controller double: retries exercise real read/modify/read logic."""

    def __init__(self, pem: bytes):
        self.pem = pem
        self.fingerprint = federation.intermediate_fingerprint(pem)
        self.cas: list[dict[str, Any]] = []
        self.groups: list[dict[str, Any]] = []
        self.writes: list[tuple[str, Any]] = []
        self.ignore_writes = False
        self.fail_groups = False
        self.concurrent = 0
        self.max_concurrent = 0
        self.definitions: list[dict[str, Any]] = []
        self.status: Any = {"connectionStatusValue": "CONNECTING"}

    def group(self, direction: str, name: str = "default") -> dict[str, str]:
        return {"caId": self.fingerprint, "group": name, "direction": direction}

    async def request(self, method: str, path: str, **options: Any) -> Any:
        if method == "GET":
            if path == "federatecertificates":
                self.concurrent += 1
                self.max_concurrent = max(self.max_concurrent, self.concurrent)
                await asyncio.sleep(0.001)
                self.concurrent -= 1
                return self.cas.copy()
            if path.startswith("federatecagroups/"):
                return self.groups.copy()
            if path == "outgoingconnections":
                return self.definitions.copy()
            if path.startswith("outgoingconnections/"):
                name = unquote(path.split("/")[1])
                return next((item for item in self.definitions if item["displayName"] == name), None)
            if path.startswith("outgoingconnectionstatus/"):
                return self.status
            raise AssertionError(path)
        self.writes.append((path, options))
        if self.ignore_writes:
            return None
        if path == "federatecertificates":
            assert options == {"pem": self.pem}
            self.cas.append({"fingerPrint": self.fingerprint})
        elif path == "federatecagroups":
            assert options["body"]["caId"] == self.fingerprint
            assert options["body"]["group"] == "default"
            direction = options["body"]["direction"]
            directions = ["INBOUND", "OUTBOUND"] if direction == "BOTH" else [direction]
            for direction in directions:
                if direction == "OUTBOUND" and self.fail_groups:
                    raise TimeoutError()
                self.groups.append(self.group(direction))
        elif path == "outgoingconnections":
            self.definitions.append(options["body"])
        else:
            raise AssertionError(path)
        return None


@pytest.fixture
def tak(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeTAK:
    state = FakeTAK(make_cert())
    monkeypatch.setattr(config, "TAK_CERTS_FOLDER", tmp_path)
    monkeypatch.setattr(federation, "download_intermediate", AsyncMock(return_value=state.pem))
    monkeypatch.setattr(RestHelpers, "federation_request", lambda self, *args, **kwargs: state.request(*args, **kwargs))
    return state


def operation() -> federation.FederationOperation:
    return federation.FederationOperation(FederationRequest(remote_base=PEER))


@pytest.mark.asyncio
async def test_trust_retry(tak: FakeTAK) -> None:
    tak.cas.append({"fingerPrint": "unrelated"})
    tak.groups.append(tak.group("INBOUND", "unrelated"))
    result = await operation().run()
    assert result == {"remote_base": PEER, "changed": True, "ca_fingerprint": tak.fingerprint}
    assert tak.writes[1][1]["body"]["direction"] == "BOTH"
    assert (await operation().run())["changed"] is False
    assert len(tak.writes) == 2
    assert tak.cas[0] == {"fingerPrint": "unrelated"}
    assert tak.groups[0]["group"] == "unrelated"


@pytest.mark.asyncio
async def test_partial_group_failure_retry(tak: FakeTAK) -> None:
    tak.fail_groups = True
    with pytest.raises(HTTPException) as exc:
        await operation().run()
    assert exc.value.status_code == 504
    assert exc.value.detail["stage"] == "groups"
    assert exc.value.detail["may_have_changed"] is True
    tak.fail_groups = False
    await operation().run()
    assert tak.writes[-1][1]["body"]["direction"] == "OUTBOUND"
    assert tak.groups == [tak.group("INBOUND"), tak.group("OUTBOUND")]


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["INBOUND", "OUTBOUND"])
async def test_missing_direction(tak: FakeTAK, direction: str) -> None:
    tak.cas.append({"fingerPrint": tak.fingerprint})
    tak.groups.append(tak.group(direction))
    assert (await operation().run())["changed"] is True
    assert len(tak.writes) == 1
    assert tak.writes[0][1]["body"]["direction"] != direction


@pytest.mark.asyncio
async def test_upload_readback_failure(tak: FakeTAK) -> None:
    tak.ignore_writes = True
    with pytest.raises(HTTPException) as exc:
        await operation().run()
    assert exc.value.status_code == 502
    assert exc.value.detail["code"] == "ca_readback_failed"
    assert exc.value.detail["may_have_changed"] is True
    assert len(tak.writes) == 1


@pytest.mark.asyncio
async def test_groups_readback_failure(tak: FakeTAK) -> None:
    tak.cas.append({"fingerPrint": tak.fingerprint})
    tak.ignore_writes = True
    with pytest.raises(HTTPException) as exc:
        await operation().run()
    assert exc.value.detail["code"] == "groups_readback_failed"


@pytest.mark.asyncio
async def test_concurrent_requests(tak: FakeTAK) -> None:
    results = await asyncio.gather(operation().run(), operation().run())
    assert sorted(result["changed"] for result in results) == [False, True]
    assert len(tak.writes) == 2
    assert tak.max_concurrent == 1


@pytest.mark.asyncio
async def test_busy_lock(tak: FakeTAK, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(federation, "LOCK_SECONDS", 0.02)
    with filelock.FileLock(config.TAK_CERTS_FOLDER / "federation.lock"), pytest.raises(HTTPException) as exc:
        await operation().run()
    assert exc.value.status_code == 503
    assert exc.value.detail["may_have_changed"] is False
    assert tak.writes == []


@pytest.mark.asyncio
async def test_deadline_releases_lock(tak: FakeTAK, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(federation, "OPERATION_SECONDS", 0.01)
    with monkeypatch.context() as patch:

        async def stall(*args: Any, **kwargs: Any) -> None:
            await asyncio.sleep(1)

        patch.setattr(RestHelpers, "federation_request", stall)
        with pytest.raises(HTTPException) as exc:
            await operation().run()
        assert exc.value.status_code == 504
    with filelock.FileLock(config.TAK_CERTS_FOLDER / "federation.lock").acquire(timeout=0):
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [ValueError("private data"), aiohttp.ClientConnectionError("private data")])
async def test_fetch_failure(tak: FakeTAK, monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    monkeypatch.setattr(federation, "download_intermediate", AsyncMock(side_effect=error))
    with pytest.raises(HTTPException) as exc:
        await operation().run()
    assert exc.value.status_code == 502
    assert exc.value.detail["stage"] == "fetch_ca"
    assert "private data" not in str(exc.value.detail)
    assert tak.writes == []


@pytest.mark.asyncio
async def test_invalid_certificate_no_write(tak: FakeTAK, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(federation, "download_intermediate", AsyncMock(return_value=make_cert(root=True)))
    with pytest.raises(HTTPException) as exc:
        await operation().run()
    assert exc.value.status_code == 502
    assert tak.writes == []


def test_trust_route(tak: FakeTAK, rmclient: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("AUDIT", logger="takrmapi.api.federation"):
        result = rmclient.post("/api/v1/federation/trust", json={"remote_base": PEER})
    assert result.status_code == 200
    assert result.json()["directions"] == ["INBOUND", "OUTBOUND"]
    assert result.json()["operation"] == "trust"
    assert any(
        record.levelname == "AUDIT" and f"action=trust peer={PEER} result=success changed=True" in record.message
        for record in caplog.records
    )


def test_trust_failure_audit(tak: FakeTAK, rmclient: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    tak.fail_groups = True
    with caplog.at_level("AUDIT", logger="takrmapi.api.federation"):
        response = rmclient.post("/api/v1/federation/trust", json={"remote_base": PEER})
    assert response.status_code == 504
    assert any(
        f"action=trust peer={PEER} result=failed status=504 stage=groups" in record.message for record in caplog.records
    )


def test_self_federation(tak: FakeTAK, rmclient: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("AUDIT", logger="takrmapi.api.federation"):
        response = rmclient.post("/api/v1/federation/trust", json={"remote_base": "localmaeher.dev.pvarki.fi:4439"})
    assert response.status_code == 422
    assert any("result=failed status=422 stage=authorize" in record.message for record in caplog.records)
    assert tak.writes == []
    federation.download_intermediate.assert_not_called()


async def prepare_trust(tak: FakeTAK) -> None:
    tak.cas.append({"fingerPrint": tak.fingerprint})
    tak.groups.extend([tak.group("INBOUND"), tak.group("OUTBOUND")])


@pytest.mark.asyncio
async def test_outgoing_retry(tak: FakeTAK) -> None:
    await prepare_trust(tak)
    result = await operation().run(outgoing=True)
    assert result["changed"] is True
    assert result["display_name"] == "fast_flounder"
    assert result["connection_status"] == "CONNECTING"
    assert tak.writes == [
        (
            "outgoingconnections",
            {
                "body": {
                    "displayName": "fast_flounder",
                    "address": f"tak.{PEER}",
                    "port": 9001,
                    "enabled": True,
                    "protocolVersion": 2,
                    "reconnectInterval": 30,
                    "unlimitedRetries": True,
                    "tls": True,
                    "useToken": False,
                }
            },
        )
    ]
    assert (await operation().run(outgoing=True))["changed"] is False
    assert len(tak.writes) == 1


@pytest.mark.asyncio
async def test_outgoing_other_name(tak: FakeTAK) -> None:
    await prepare_trust(tak)
    await operation().run(outgoing=True)
    tak.definitions[0]["displayName"] = "fast flounder"
    tak.definitions[0]["address"] = f"TAK.{PEER.upper()}"
    tak.writes.clear()
    result = await operation().run(outgoing=True)
    assert result["display_name"] == "fast flounder"
    assert result["changed"] is False
    assert tak.writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override",
    [
        {"enabled": False},
        {"protocolVersion": 1},
        {"tls": False},
        {"useToken": True},
        {"reconnectInterval": 1},
        {"unlimitedRetries": False},
        {"address": "tak.another.example"},
        {"port": 9002},
    ],
)
async def test_outgoing_conflict(tak: FakeTAK, override: dict[str, Any]) -> None:
    await prepare_trust(tak)
    await operation().run(outgoing=True)
    tak.definitions[0].update(override)
    before = tak.definitions[0].copy()
    tak.writes.clear()
    with pytest.raises(HTTPException) as exc:
        await operation().run(outgoing=True)
    assert exc.value.status_code == 409
    assert exc.value.detail["may_have_changed"] is False
    assert tak.definitions == [before]
    assert tak.writes == []


@pytest.mark.asyncio
async def test_outgoing_duplicates(tak: FakeTAK) -> None:
    await prepare_trust(tak)
    await operation().run(outgoing=True)
    tak.definitions.append({**tak.definitions[0], "displayName": "another"})
    tak.writes.clear()
    with pytest.raises(HTTPException) as exc:
        await operation().run(outgoing=True)
    assert exc.value.status_code == 409
    assert tak.writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize("ca,directions", [(False, []), (True, []), (True, ["INBOUND"]), (True, ["OUTBOUND"])])
async def test_outgoing_requires_trust(tak: FakeTAK, ca: bool, directions: list[str]) -> None:
    if ca:
        tak.cas.append({"fingerPrint": tak.fingerprint})
    tak.groups.extend(tak.group(direction) for direction in directions)
    with pytest.raises(HTTPException) as exc:
        await operation().run(outgoing=True)
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "trust_required"
    assert tak.writes == []


@pytest.mark.asyncio
async def test_outgoing_readback_failure(tak: FakeTAK) -> None:
    await prepare_trust(tak)
    tak.ignore_writes = True
    with pytest.raises(HTTPException) as exc:
        await operation().run(outgoing=True)
    assert exc.value.status_code == 502
    assert exc.value.detail["code"] == "outgoing_readback_failed"
    assert exc.value.detail["may_have_changed"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [None, {}, {"connectionStatusValue": "CONNECTED"}])
async def test_outgoing_status(tak: FakeTAK, status: Any) -> None:
    await prepare_trust(tak)
    tak.status = status
    result = await operation().run(outgoing=True)
    assert result["connection_status"] == (status.get("connectionStatusValue") if status else None)


@pytest.mark.asyncio
async def test_concurrent_outgoing(tak: FakeTAK) -> None:
    await prepare_trust(tak)
    results = await asyncio.gather(operation().run(outgoing=True), operation().run(outgoing=True))
    assert sorted(result["changed"] for result in results) == [False, True]
    assert len(tak.writes) == 1


def test_outgoing_route(tak: FakeTAK, rmclient: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    tak.cas.append({"fingerPrint": tak.fingerprint})
    tak.groups.extend([tak.group("INBOUND"), tak.group("OUTBOUND")])
    with caplog.at_level("AUDIT", logger="takrmapi.api.federation"):
        response = rmclient.post("/api/v1/federation/outgoing", json={"remote_base": PEER})
    assert response.status_code == 200
    result = response.json()
    assert result["operation"] == "outgoing"
    assert result["protocol_version"] == 2
    assert result["port"] == 9001
    assert result["enabled"] is True
    assert any(
        f"action=outgoing peer={PEER} result=success changed=True" in record.message for record in caplog.records
    )


@pytest.mark.parametrize("endpoint", ["trust", "outgoing"])
def test_no_certificate(tak: FakeTAK, rmclient: TestClient, endpoint: str) -> None:
    rmclient.headers.pop("X-ClientCert-DN")
    response = rmclient.post(f"/api/v1/federation/{endpoint}", json={"remote_base": PEER})
    assert response.status_code == 403
    federation.download_intermediate.assert_not_called()


@pytest.mark.parametrize("endpoint", ["trust", "outgoing"])
def test_proxy_cannot_override_policy(
    tak: FakeTAK, rmclient: TestClient, endpoint: str, caplog: pytest.LogCaptureFixture
) -> None:
    rmclient.headers["X-Rasenmaeher-Proxy"] = "productproxy"
    with caplog.at_level("AUDIT", logger="takrmapi.api.federation"):
        response = rmclient.post(f"/api/v1/federation/{endpoint}?allow_proxy=true", json={"remote_base": PEER})
    assert response.status_code == 403
    assert any(
        f"action={endpoint} peer={PEER} result=failed status=403 stage=authorize" in record.message
        for record in caplog.records
    )
    federation.download_intermediate.assert_not_called()


@pytest.mark.parametrize("endpoint", ["trust", "outgoing"])
def test_invalid_body(tak: FakeTAK, rmclient: TestClient, endpoint: str) -> None:
    response = rmclient.post(f"/api/v1/federation/{endpoint}", json={"remote_base": PEER, "port": 1234})
    assert response.status_code == 422
    federation.download_intermediate.assert_not_called()
