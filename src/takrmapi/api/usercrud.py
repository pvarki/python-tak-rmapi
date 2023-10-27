""""User actions"""
import logging
import base64
from typing import List, Dict
from fastapi import APIRouter, Depends
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest
from libpvarki.schemas.generic import OperationResultResponse

from takrmapi import tak_helpers

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])

test_router = APIRouter()


@router.post("/created")
async def user_created(user: UserCRUDRequest) -> OperationResultResponse:
    """New device cert was created"""
    _ = user  # TODO: should we validate the cert at this point ??

    LOGGER.info("Adding new user '{}' to TAK".format(user.callsign))

    await tak_helpers.add_new_user(callsign=user.callsign, x509cert=user.x509cert)

    # uuid: str = Field(description="RASENMAEHER UUID for this user")
    # callsign: str = Field(description="Callsign of the user")
    # x509cert: str = Field(description="Certificate encoded with CFSSL conventions (newlines escaped)")

    result = OperationResultResponse(success=True)
    return result


# While delete would be semantically better it takes no body and definitely forces the
# integration layer to keep track of UUIDs
@router.post("/revoked")
async def user_revoked(user: UserCRUDRequest) -> OperationResultResponse:
    """Device cert was revoked"""
    _ = user
    await tak_helpers.revoke_user(callsign=user.callsign)
    result = OperationResultResponse(success=True)
    return result


@router.post("/promoted")
async def user_promoted(user: UserCRUDRequest) -> OperationResultResponse:
    """Device cert was promoted to admin privileges"""
    _ = user
    await tak_helpers.promote_user(callsign=user.callsign)
    result = OperationResultResponse(success=True)
    return result


@router.post("/demoted")
async def user_demoted(user: UserCRUDRequest) -> OperationResultResponse:
    """Device cert was demoted to standard privileges"""
    _ = user
    await tak_helpers.demote_user(callsign=user.callsign)
    result = OperationResultResponse(success=True)
    return result


@router.put("/updated")
async def user_updated(user: UserCRUDRequest) -> OperationResultResponse:
    """Device callsign updated"""
    _ = user
    await tak_helpers.update_user(callsign=user.callsign, x509cert=user.x509cert)
    result = OperationResultResponse(success=True)
    return result


@router.get("/missionzip")
async def get_missionpkg(user: UserCRUDRequest) -> List[Dict[str, str]]:
    """Return zip package containing client config and certificates"""
    _ = user
    zip_files = await tak_helpers.create_missionpkg(callsign=user.callsign, missionpkg="example")
    returnable: List[Dict[str, str]] = []
    for file in zip_files:
        with open(file, "rb") as filehandle:
            contents = filehandle.read()
        filename = file.split("/")[-1]
        returnable.append(
            {
                "title": filename,
                "data": f"data:application/zip;base64,{base64.b64encode(contents).decode('ascii')}",
                "filename": f"{user.callsign}_{filename}",
            }
        )
    return returnable


# REMOVE ME, JUST FOR TESTING
@router.get("/test-list-m")
async def test_user_listm() -> OperationResultResponse:
    """Device callsign updated"""
    await tak_helpers.tak_api_user_list()

    result = OperationResultResponse(success=True)
    return result


# REMOVE ME, JUST FOR TESTING
@test_router.get("/test-list")
async def user_list() -> OperationResultResponse:
    """Device callsign updated"""
    await tak_helpers.tak_api_user_list()
    result = OperationResultResponse(success=True)
    return result
