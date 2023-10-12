"""Endpoints for information for the admin"""
import logging
import os
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from libpvarki.middleware import MTLSHeader

LOGGER = logging.getLogger(__name__)

mtls_router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])
router = APIRouter()


@router.get("")
async def get_healthcheck() -> Dict[Any, Any]:
    """Basic healthcheck"""
    returnable: Dict[Any, Any] = {"healthcheck": "success"}
    return returnable


@router.get("/delivery_status")
async def get_healthcheck_delivery_status(
    request: Request,
) -> Dict[Any, Any]:
    """Return 200 when api is ready to deliver"""
    ready_to_serve: bool = False

    # TODO do some actual logic to check if we have something to serve...
    dir_files = os.listdir("/opt/tak/data/certs/files")
    if len(dir_files) > 0:
        ready_to_serve = True

    if not ready_to_serve:
        _reason = "Waiting for RM to give go ahead."
        LOGGER.info("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=420, detail=_reason)

    returnable: Dict[Any, Any] = {"status": "rdy-to-serve"}
    return returnable
