""""User actions"""

import logging
from fastapi import APIRouter, Depends, Request
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest
from libpvarki.schemas.generic import OperationResultResponse

from .. import tak_helpers
from .helpers import comes_from_rm

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.post("/created")
async def user_created(user: UserCRUDRequest, request: Request) -> OperationResultResponse:
    """New device cert was created"""
    comes_from_rm(request)
    tak_usercrud = tak_helpers.UserCRUD(user)
    LOGGER.info("Adding new user '{}' to TAK".format(user.callsign))
    await tak_usercrud.add_new_user()

    result = OperationResultResponse(success=True)
    return result


# While delete would be semantically better it takes no body and definitely forces the
# integration layer to keep track of UUIDs
@router.post("/revoked")
async def user_revoked(user: UserCRUDRequest, request: Request) -> OperationResultResponse:
    """Device cert was revoked"""
    comes_from_rm(request)
    tak_usercrud = tak_helpers.UserCRUD(user)
    LOGGER.info("Removing user '{}' from TAK".format(user.callsign))
    await tak_usercrud.revoke_user()
    result = OperationResultResponse(success=True)
    return result


@router.post("/promoted")
async def user_promoted(user: UserCRUDRequest, request: Request) -> OperationResultResponse:
    """Device cert was promoted to admin privileges"""
    comes_from_rm(request)
    tak_usercrud = tak_helpers.UserCRUD(user)
    LOGGER.info("Promoting user '{}' to admin".format(user.callsign))
    await tak_usercrud.promote_user()
    result = OperationResultResponse(success=True)
    return result


@router.post("/demoted")
async def user_demoted(user: UserCRUDRequest, request: Request) -> OperationResultResponse:
    """Device cert was demoted to standard privileges"""
    comes_from_rm(request)
    tak_usercrud = tak_helpers.UserCRUD(user)
    LOGGER.info("Demoting user '{}' to normal user".format(user.callsign))
    await tak_usercrud.demote_user()
    result = OperationResultResponse(success=True)
    return result


@router.put("/updated")
async def user_updated(user: UserCRUDRequest, request: Request) -> OperationResultResponse:
    """Device callsign updated"""
    comes_from_rm(request)
    tak_usercrud = tak_helpers.UserCRUD(user)
    await tak_usercrud.update_user()
    result = OperationResultResponse(success=True)
    return result
