"""Test the HTML fragment"""

from typing import Dict
import logging


import pytest
from fastapi.testclient import TestClient

LOGGER = logging.getLogger(__name__)
pytestmark = pytest.mark.skip(
    reason="tests need complete refactoring and most of them can't work without working RASENMAHER instance anymore",
)


def test_description(norppa11: Dict[str, str], mtlsclient: TestClient) -> None:
    """Check that getting fragment works"""
    resp = mtlsclient.post("/api/v1/description/en", json=norppa11)
    assert resp.status_code == 200
    payload = resp.json()
    assert "callsign" in payload
