"""Routes for interoperation between products"""

from typing import Sequence, Optional
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request, HTTPException
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.generic import OperationResultResponse
from libpvarki.schemas.product import UserCRUDRequest
from pydantic import Field, BaseModel, ConfigDict, Extra  # pylint: disable=E0611  # False positive


from .helpers import comes_from_rm
from ..tak_helpers import UserCRUD as TAKBaseCRUD
from ..tak_helpers import Helpers as TAKBaseHelper
from .. import config


LOGGER = logging.getLogger(__name__)

interoprouter = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


# FIXME: Move to libpvarki
class ProductAddRequest(BaseModel):  # pylint: disable=too-few-public-methods
    """Request to add product interoperability."""

    certcn: str = Field(description="CN of the certificate")
    x509cert: str = Field(description="Certificate encoded with CFSSL conventions (newlines escaped)")

    model_config = ConfigDict(
        extra=Extra.forbid,
        schema_extra={
            "examples": [
                {
                    "certcn": "product.deployment.tld",
                    "x509cert": "-----BEGIN CERTIFICATE-----\\nMIIEwjCC...\\n-----END CERTIFICATE-----\\n",
                },
            ],
        },
    )


# FIXME: Move to libpvarki
class ProductAuthzResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Authz info"""

    type: str = Field(description="type of authz: bearer-token, basic, mtls")
    token: Optional[str] = Field(description="Bearer token", default=None)
    username: Optional[str] = Field(description="Username for basic auth", default=None)
    password: Optional[str] = Field(description="Password for basic auth", default=None)

    model_config = ConfigDict(
        extra=Extra.forbid,
        schema_extra={
            "examples": [
                {
                    "type": "mtls",
                },
                {
                    "type": "bearer-token",
                    "token": "<JWT>",
                },
                {
                    "type": "basic",
                    "username": "product.deployment.tld",
                    "password": "<PASSWORD>",
                },
            ],
        },
    )


def cn_to_callsign(certcn: str) -> str:
    """Convert CN to something that is valid as callsign filename"""
    return certcn.replace(".", "_")


class ProductCRUD(TAKBaseCRUD):
    """Pretend to be user"""

    def __init__(self, user: UserCRUDRequest):
        super().__init__(user)
        self.helpers = TakProductHelper(self)
        self.write_cert_conditional()

    @property
    def certpath(self) -> Path:
        """Path to local cert"""
        return config.TAK_CERTS_FOLDER / f"{self.certcn}_rm.pem"

    def write_cert_conditional(self) -> None:
        """write the X509 cert if it did not exist"""
        if self.certpath.exists():
            return
        if self.user.x509cert == "NOTHERE":
            raise HTTPException(status_code=404, detail="Certificate not set")
        self.certpath.parent.mkdir(parents=True, exist_ok=True)
        self.certpath.write_text(self.rm_certpem)


class TakProductHelper(TAKBaseHelper):  # pylint: disable=too-few-public-methods
    """Do TAK things"""

    @property
    def enable_user_cert_names(self) -> Sequence[str]:
        """Return the stems for cert PEM files"""
        return (f"{self.user.callsign}_rm",)


@interoprouter.post("/add")
async def add_product(
    product: ProductAddRequest,
    request: Request,
) -> OperationResultResponse:
    """Product needs interop privileges. This can only be called by RASENMAEHER"""
    comes_from_rm(request)
    callsign = cn_to_callsign(product.certcn)
    product_user = UserCRUDRequest(
        uuid=callsign,
        callsign=callsign,
        x509cert=product.x509cert,
    )
    crud = ProductCRUD(product_user)
    res = await crud.helpers.add_admin_to_tak_with_cert()
    if not res:
        return OperationResultResponse(success=False, error="TAK admin script failed")
    return OperationResultResponse(success=True)


@interoprouter.get("/authz")
async def get_authz(
    request: Request,
) -> ProductAuthzResponse:
    """Get authz info for the product, for tak it's always mtls"""
    payload = request.state.mtlsdn
    callsign = cn_to_callsign(payload.get("CN"))
    product_user = UserCRUDRequest(
        uuid=callsign,
        callsign=callsign,
        x509cert="NOTHERE",
    )
    crud = ProductCRUD(product_user)
    if not crud.certpath.exists():
        raise HTTPException(status_code=404, detail="Certificate does not exist")
    result = ProductAuthzResponse(type="mtls")
    return result
