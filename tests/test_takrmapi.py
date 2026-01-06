"""Package level tests"""

import base64
import time
from secrets import token_bytes

from unittest import mock

import pytest

from takrmapi import __version__
from takrmapi.api.tak_missionpackage import (
    generate_encrypted_ephemeral_url_fragment,
    parse_encrypted_ephemeral_url_fragment,
)
from takrmapi.takutils.tak_pkg_helpers import TAKDataPackage


def test_version() -> None:
    """Make sure version matches expected"""
    assert __version__ == "1.10.0"


@pytest.fixture(autouse=True)
def clear_encryption_keys() -> None:
    """Clear ephemeral keys between tests."""
    TAKDataPackage.ephemeral_key = b""


@mock.patch("os.environ", {"TAKRMAPI_SECRET_KEY": base64.b64encode(token_bytes(32)).decode("utf-8")})
def test_ephemeral_link_generation() -> None:
    """Verify that ephemeral link generation works as expected."""
    now = time.time()
    callsign = "N0CALL"
    uuid = "12345678-1234-5678-1234-567812345678"

    encrypted_url = generate_encrypted_ephemeral_url_fragment(callsign, uuid, "testvariant", now)
    assert "testvariant" not in encrypted_url

    gotten_callsign, gotten_uuid, gotten_variant = parse_encrypted_ephemeral_url_fragment(encrypted_url)
    assert gotten_callsign == callsign
    assert gotten_uuid == uuid
    assert gotten_variant == "testvariant"


EXAMPLE_KEY = "zyygdR6MGvmCe+Dm5hDMdQqTJa7VNc451SyQrirUXUI="  # pragma: allowlist secret


@mock.patch("os.environ", {"TAKRMAPI_SECRET_KEY": EXAMPLE_KEY})
def test_ephemeral_key_loading() -> None:
    """Verify that ephemeral key loading works as expected."""
    assert TAKDataPackage.get_ephemeral_byteskey() != b""
    assert len(TAKDataPackage.get_ephemeral_byteskey()) == 32
    assert base64.b64encode(TAKDataPackage.get_ephemeral_byteskey()).decode("ascii") == EXAMPLE_KEY
