"""Routes for interoperation between products"""

import logging

from fastapi import APIRouter, Depends, Request
from libpvarki.middleware.mtlsheader import MTLSHeader
from libpvarki.schemas.generic import OperationResultResponse

from takrmapi.takutils import tak_helpers

from .schemas import ProductAddRequest
from .usercrud import comes_from_rm

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.post("/add")
async def add_product(product: ProductAddRequest, request: Request) -> OperationResultResponse:
    """Product needs interop privileges. This can only be called by RASENMAEHER"""
    comes_from_rm(request)
    LOGGER.info("Enrolling product %s into TAK", product.certcn)
    if not await tak_helpers.enroll_peer_product_cert(product.certcn, product.x509cert):
        return OperationResultResponse(success=False, error="Could not enrol the certificate into TAK")
    return OperationResultResponse(success=True)
