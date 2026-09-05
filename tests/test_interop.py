"""Test the product interoperability endpoint"""

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from takrmapi import config
from takrmapi.takutils import tak_helpers

from .conftest import APP

LOGGER = logging.getLogger(__name__)

# pylint: disable=redefined-outer-name

PAYLOAD = {"certcn": "bl.localmaeher.dev.pvarki.fi", "x509cert": "-----BEGIN CERTIFICATE-----\\nnope\\n"}

# Not folded into test_comes_from_rm.py's parametrised sweep: that posts a
# user-shaped body, which fails ProductAddRequest validation with a 422 before
# the CN guard ever runs.


def test_no_cert() -> None:
    """Without an mTLS header the endpoint must not be reachable"""
    client = TestClient(APP)
    assert client.post("/api/v1/interop/add", json=PAYLOAD).status_code == 403


def test_wrong_cn(mtlsclient: TestClient) -> None:
    """Only RASENMAEHER may enrol a peer product, any other CN gets 403"""
    assert mtlsclient.post("/api/v1/interop/add", json=PAYLOAD).status_code == 403


@pytest.mark.asyncio
async def test_garbage_cert_is_refused() -> None:
    """A cert that will not parse must be refused before anything is written or shelled out"""
    assert await tak_helpers.enroll_peer_product_cert("bl.example.com", "not a certificate") is False


@pytest.mark.parametrize(
    "certcn",
    [
        "a$(touch PWNED_A)",
        "b;touch PWNED_B",
        "c`touch PWNED_C`",
        "bl.example.com;touch${IFS}PWNED;#",
        "../../../../etc/evil",
        "has space",
        "",
    ],
)
@pytest.mark.asyncio
async def test_enroll_peer_rejects_unsafe_cn(certcn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A CN that is not a plain DNS-style name must be refused before any file or shell work."""
    monkeypatch.setattr(config, "TAK_CERTS_FOLDER", tmp_path)

    async def _boom(*args: object, **kwargs: object) -> object:
        raise AssertionError(f"call_cmd must not run for certcn={certcn!r}")

    monkeypatch.setattr(tak_helpers, "call_cmd", _boom)

    assert await tak_helpers.enroll_peer_product_cert(certcn, "-----BEGIN CERTIFICATE-----\nx\n") is False
    assert list(tmp_path.iterdir()) == []
