"""Test enrollment endpoint"""
import logging
from typing import Dict, Any
import pytest

# from libadvian.binpackers import uuid_to_b64, b64_to_uuid
from async_asgi_testclient import TestClient  # pylint: disable=import-error

LOGGER = logging.getLogger(__name__)


#
# Check the conftest.py from python-rasenmaeher-api and get the latest app_client code from there...
# It might or might not have something new...
#


# @pytest.mark.asyncio
# @pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
# async def test_post_enrollment_config_setstate_success_work_id(app_client: TestClient) -> None:
#    """
#    /config/set-state
#    Result should be successful
#    """
#    json_dict: Dict[Any, Any] = {
#        "state": "testing",
#        "work_id": "koira",
#        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
#    }
#    resp = await app_client.post("/api/v1/cmd/run-something", json=json_dict)
#    resp_dict: Dict[Any, Any] = resp.json()
#    # print("###########")
#    # print(resp)
#    # print(resp.json())
#    # print("###########")
#    assert resp.status_code == 200
#    assert resp_dict["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_config_active_config(app_client: TestClient) -> None:
    """
    /config/active-config
    at least "success" should come in response json
    """
    resp = await app_client.get("/api/v1/config/active-config")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert resp_dict["success"] is not None
