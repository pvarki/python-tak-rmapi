"""Test the product interoperability endpoint"""

import logging

import pytest
from fastapi.testclient import TestClient

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
