"""Test that endpoints RASENMAEHER owns are not reachable by regular users"""

from typing import Any, Dict
import logging

import pytest
import httpx
from fastapi.testclient import TestClient

LOGGER = logging.getLogger(__name__)

RM_ONLY_ENDPOINTS = (
    ("post", "/api/v1/users/created"),
    ("post", "/api/v1/users/revoked"),
    ("post", "/api/v1/users/promoted"),
    ("post", "/api/v1/users/demoted"),
    ("put", "/api/v1/users/updated"),
    ("get", "/api/v2/admin/description/en"),
)


def call(client: TestClient, method: str, path: str, payload: Dict[str, Any]) -> httpx.Response:
    """Call the endpoint, GET does not take a body"""
    if method == "get":
        return client.get(path)
    return getattr(client, method)(path, json=payload)


@pytest.mark.parametrize("method,path", RM_ONLY_ENDPOINTS)
def test_wrong_cn(method: str, path: str, norppa11: Dict[str, str], mtlsclient: TestClient) -> None:
    """A valid cert that is not RASENMAEHERs must not be enough, this is the actual fix"""
    resp = call(mtlsclient, method, path, norppa11)
    assert resp.status_code == 403


@pytest.mark.parametrize("method,path", RM_ONLY_ENDPOINTS)
def test_proxy_disallow(method: str, path: str, norppa11: Dict[str, str], rmclient: TestClient) -> None:
    """RASENMAEHERs cert is not enough if the call was made on behalf of an end-user"""
    rmclient.headers.update(
        {
            "X-Rasenmaeher-Proxy": "productproxy",
            "X-Proxy-Callsign": norppa11["callsign"],
        }
    )
    resp = call(rmclient, method, path, norppa11)
    assert resp.status_code == 403


def test_admin_description_allowed(rmclient: TestClient) -> None:
    """RASENMAEHER itself still gets the admin description"""
    resp = rmclient.get("/api/v2/admin/description/en")
    assert resp.status_code == 200
    assert resp.json()["shortname"] == "tak-server"
