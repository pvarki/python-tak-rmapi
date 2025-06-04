""""User actions"""

import logging
from fastapi import APIRouter, Depends
from pathlib import Path
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest
from libpvarki.schemas.generic import OperationResultResponse

from typing import Any, Dict
from takrmapi import tak_helpers, config

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])

test_router = APIRouter()


@router.post("/created")
async def user_created(user: UserCRUDRequest) -> OperationResultResponse:
    """New device cert was created"""
    tak_usercrud = tak_helpers.UserCRUD(user)
    LOGGER.info("Adding new user '{}' to TAK".format(user.callsign))
    await tak_usercrud.add_new_user()

    result = OperationResultResponse(success=True)
    return result


# While delete would be semantically better it takes no body and definitely forces the
# integration layer to keep track of UUIDs
@router.post("/revoked")
async def user_revoked(user: UserCRUDRequest) -> OperationResultResponse:
    """Device cert was revoked"""
    tak_usercrud = tak_helpers.UserCRUD(user)
    LOGGER.info("Removing user '{}' from TAK".format(user.callsign))
    await tak_usercrud.revoke_user()
    result = OperationResultResponse(success=True)
    return result


@router.post("/promoted")
async def user_promoted(user: UserCRUDRequest) -> OperationResultResponse:
    """Device cert was promoted to admin privileges"""
    tak_usercrud = tak_helpers.UserCRUD(user)
    LOGGER.info("Promoting user '{}' to admin".format(user.callsign))
    await tak_usercrud.promote_user()
    result = OperationResultResponse(success=True)
    return result


@router.post("/demoted")
async def user_demoted(user: UserCRUDRequest) -> OperationResultResponse:
    """Device cert was demoted to standard privileges"""
    tak_usercrud = tak_helpers.UserCRUD(user)
    LOGGER.info("Demoting user '{}' to normal user".format(user.callsign))
    await tak_usercrud.demote_user()
    result = OperationResultResponse(success=True)
    return result


@router.put("/updated")
async def user_updated(user: UserCRUDRequest) -> OperationResultResponse:
    """Device callsign updated"""
    tak_usercrud = tak_helpers.UserCRUD(user)
    await tak_usercrud.update_user()
    result = OperationResultResponse(success=True)
    return result


# REMOVE ME, JUST FOR TESTING
@router.get("/test-list-m")
async def test_user_listm() -> OperationResultResponse:
    """Get user listing from TAK rest api"""
    t_rest_helper = tak_helpers.RestHelpers()
    await t_rest_helper.tak_api_user_list()
    result = OperationResultResponse(success=True)
    return result

# Get current mission list, TESTING
@router.get("/get-mission-list")
async def get_mission_list() -> Dict[Any,Any]:
    """ Testing - get mission list"""
    t_rest_helper = tak_helpers.RestHelpers()
    data = await t_rest_helper.tak_api_mission_get(groupname="RECON")
    tmp_return: Dict[Any,Any] = {"mission found":data}
    return tmp_return

# Add current mission list, TESTING
@router.get("/put-mission")
async def put_mission() -> Dict[Any,Any]:
    """ Testing - put mission """
    t_rest_helper = tak_helpers.RestHelpers()
    result = await t_rest_helper.tak_api_mission_put(
        groupname="RECON",
        description="Recon feed for validated information",
        defaultRole="MISSION_SUBSCRIBER",
        )
    tmp_return: Dict[Any,Any] = {"mission added":result}
    return tmp_return

# Add current mission list, TESTING
@router.get("/put-mission-keywords")
async def put_mission_keywords() -> Dict[Any,Any]:
    """ Testing - get mission """
    t_rest_helper = tak_helpers.RestHelpers()
    result = await t_rest_helper.tak_api_mission_keywords(
        groupname="RECON",
        keywords=["#RECON"]
        )
    tmp_return: Dict[Any,Any] = {"keywords added":result}
    return tmp_return



# List device profile, TESTING
@router.get("/list-device-profile")
async def get_dev_profile() -> Dict[Any,Any]:
    """ Testing - list device profile """
    t_rest_helper = tak_helpers.RestHelpers()
    result = await t_rest_helper.tak_api_get_device_profile(
        profile_name="Default-ATAK2",
        )
    tmp_return: Dict[Any,Any] = {"profile added":result}
    return tmp_return

# List device profile files, TESTING
@router.get("/list-device-profile-files")
async def get_dev_profile_files() -> Dict[Any,Any]:
    """ Testing - list device profile """
    t_rest_helper = tak_helpers.RestHelpers()
    result = await t_rest_helper.tak_api_get_device_profile_files(
        profile_name="Default-ATAK",
        )
    tmp_return: Dict[Any,Any] = {"profile added":result}
    return tmp_return

# Add current mission list, TESTING
@router.get("/add-device-profile")
async def add_dev_profile() -> Dict[Any,Any]:
    """ Testing - add device profile """
    t_rest_helper = tak_helpers.RestHelpers()
    result = await t_rest_helper.tak_api_add_device_profile(
        profile_name="Default-ATAK",
        groups=["default"]
        )
    tmp_return: Dict[Any,Any] = {"profile added":result}
    return tmp_return

# Add current mission list, TESTING
@router.get("/update-device-profile")
async def update_dev_profile() -> Dict[Any,Any]:
    """ Testing - update device profile """
    t_rest_helper = tak_helpers.RestHelpers()
    result = await t_rest_helper.tak_api_update_device_profile(
        profile_name="Default-ATAK",
        profile_active=True,
        apply_on_connect=True,
        apply_on_enrollment=False,
        profile_type="Connection",
        groups=["default"]
        )
    tmp_return: Dict[Any,Any] = {"profile updated":result}
    return tmp_return

# Add current mission list, TESTING
@router.get("/upload-file-to-profile")
async def upload_file_to_profile() -> Dict[Any,Any]:
    """ Testing - add device profile """
    t_rest_helper = tak_helpers.RestHelpers()
    result = await t_rest_helper.tak_api_upload_file_to_profile(
        profile_name="Default-ATAK",
        file_path= Path(config.TEMPLATES_PATH / 
            "tak_datapackage" / 
            "default" / 
            "ATAK default settings" /
            "TAK_defaults.pref" ) 
        )
    tmp_return: Dict[Any,Any] = {"profile added":result}
    return tmp_return

# REMOVE ME, JUST FOR TESTING
@test_router.get("/test-list")
async def user_list() -> OperationResultResponse:
    """Get user listing from TAK rest api, no jwt/mtls check"""
    t_rest_helper = tak_helpers.RestHelpers()
    await t_rest_helper.tak_api_user_list()
    result = OperationResultResponse(success=True)
    return result

