""""User actions"""
import logging
import base64
from typing import List, Dict
from fastapi import APIRouter, Depends
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest
from libpvarki.schemas.generic import OperationResultResponse

from takrmapi import tak_helpers
from takrmapi.tak_schema import UserMissionZipRequest

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
    await tak_usercrud.revoke_user()
    result = OperationResultResponse(success=True)
    return result


@router.post("/promoted")
async def user_promoted(user: UserCRUDRequest) -> OperationResultResponse:
    """Device cert was promoted to admin privileges"""
    tak_usercrud = tak_helpers.UserCRUD(user)
    await tak_usercrud.promote_user()
    result = OperationResultResponse(success=True)
    return result


@router.post("/demoted")
async def user_demoted(user: UserCRUDRequest) -> OperationResultResponse:
    """Device cert was demoted to standard privileges"""
    tak_usercrud = tak_helpers.UserCRUD(user)
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


@router.get("/missionzip")
async def get_missionpkg(user_mission: UserMissionZipRequest) -> List[Dict[str, str]]:
    """Return zip package containing client config and certificates"""
    tak_missionpkg = tak_helpers.MissionZip(user_mission)
    zip_files = await tak_missionpkg.create_missionpkg()
    returnable: List[Dict[str, str]] = []
    for file in zip_files:
        with open(file, "rb") as filehandle:
            contents = filehandle.read()
        filename = file.split("/")[-1]
        returnable.append(
            {
                "title": filename,
                "data": f"data:application/zip;base64,{base64.b64encode(contents).decode('ascii')}",
                "filename": f"{user_mission.callsign}_{filename}",
            }
        )
    return returnable


# REMOVE ME, JUST FOR TESTING
@router.get("/test-list-m")
async def test_user_listm() -> OperationResultResponse:
    """Get user listing from TAK rest api"""
    t_rest_helper = tak_helpers.RestHelpers()
    await t_rest_helper.tak_api_user_list()
    result = OperationResultResponse(success=True)
    return result


# REMOVE ME, JUST FOR TESTING
@test_router.get("/test-list")
async def user_list() -> OperationResultResponse:
    """Get user listing from TAK rest api, no jwt/mtls check"""
    t_rest_helper = tak_helpers.RestHelpers()
    await t_rest_helper.tak_api_user_list()
    result = OperationResultResponse(success=True)
    return result
