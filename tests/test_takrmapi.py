"""Package level tests"""

import time

from takrmapi import __version__
from takrmapi.api.tak_missionpackage import generate_encrypted_ephemeral_url_fragment, parse_encrypted_ephemeral_url_fragment


def test_version() -> None:
    """Make sure version matches expected"""
    assert __version__ == "1.10.0"


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
