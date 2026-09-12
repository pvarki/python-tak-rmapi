"""Revocation must survive failures of either TAK or the CA."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import config
from takrmapi.takutils.revocations import Revocations
from takrmapi.takutils.tak_helpers import UserCRUD

from .test_revocations import certificate


@pytest.mark.asyncio
@pytest.mark.parametrize("removed,ca_success", [(True, True), (False, True), (True, False)])
async def test_record_before_remote_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, removed: bool, ca_success: bool
) -> None:
    monkeypatch.setattr(config, "RMAPI_PERSISTENT_FOLDER", tmp_path)
    certs = tmp_path / "certs"
    certs.mkdir()
    monkeypatch.setattr(config, "TAK_CERTS_FOLDER", certs)
    tak, rm = certificate("test"), certificate("test_rm")
    crud = UserCRUD(UserCRUDRequest(uuid="test", callsign="test", x509cert=rm[0]))
    crud.userdata.mkdir(parents=True)
    crud.certpath.write_text(tak[0])
    for name in crud.helpers.enable_user_cert_names:
        (certs / f"{name}.pem").write_text("retained for retries")

    async def delete() -> bool:
        assert Revocations().contains(tak[1])
        assert Revocations().contains(rm[1])
        return removed

    response = Mock()
    response.json = AsyncMock(return_value={"success": ca_success})
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.post.return_value = response
    with (
        patch.object(crud.helpers, "user_cert_validate", AsyncMock(return_value=True)),
        patch.object(crud.helpers, "delete_user_with_cert", AsyncMock(side_effect=delete)),
        patch.object(crud.helpers, "tak_mtls_client", AsyncMock(return_value=session)),
    ):
        assert await crud.revoke_user() == (removed and ca_success)
    assert Revocations().contains(tak[1]) and Revocations().contains(rm[1])
    assert (certs / "test.pem").exists() != (removed and ca_success)
    assert (certs / "test_rm.pem").exists() != (removed and ca_success)


@pytest.mark.asyncio
async def test_known_main_certificate_blocked_when_local_files_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "RMAPI_PERSISTENT_FOLDER", tmp_path)
    rm = certificate("test_rm")
    crud = UserCRUD(UserCRUDRequest(uuid="test", callsign="test", x509cert=rm[0]))
    with patch.object(crud.helpers, "user_cert_validate", AsyncMock(return_value=False)):
        assert not await crud.revoke_user()
    assert Revocations().contains(rm[1])


def test_incomplete_revocation_is_not_reported_as_success(rmclient: TestClient) -> None:
    with patch.object(UserCRUD, "revoke_user", AsyncMock(return_value=False)):
        response = rmclient.post("/api/v1/users/revoked", json={"uuid": "test", "callsign": "test", "x509cert": "test"})
    assert response.status_code == 503
