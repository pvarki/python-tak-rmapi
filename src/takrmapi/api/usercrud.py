""""User actions"""
import logging

from fastapi import APIRouter, Depends
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest
from libpvarki.schemas.generic import OperationResultResponse


LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.post("/created")
async def user_created(user: UserCRUDRequest) -> OperationResultResponse:
    """New device cert was created"""
    _ = user  # TODO: should we validate the cert at this point ??
    result = OperationResultResponse(success=True)
    return result


# While delete would be semantically better it takes no body and definitely forces the
# integration layer to keep track of UUIDs
@router.post("/revoked")
async def user_revoked(user: UserCRUDRequest) -> OperationResultResponse:
    """Device cert was revoked"""
    _ = user
    result = OperationResultResponse(success=True)
    return result


@router.post("/promoted")
async def user_promoted(user: UserCRUDRequest) -> OperationResultResponse:
    """Device cert was promoted to admin privileges"""
    _ = user
    result = OperationResultResponse(success=True)
    return result


@router.post("/demoted")
async def user_demoted(user: UserCRUDRequest) -> OperationResultResponse:
    """Device cert was demoted to standard privileges"""
    _ = user
    result = OperationResultResponse(success=True)
    return result


@router.put("/updated")
async def user_updated(user: UserCRUDRequest) -> OperationResultResponse:
    """Device callsign updated"""
    _ = user
    result = OperationResultResponse(success=True)
    return result
