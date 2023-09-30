"""Endpoints for information for the end-user"""
import logging

from fastapi import APIRouter, Depends
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserInstructionFragment, UserCRUDRequest
from jinja2 import Environment, FileSystemLoader

from ..config import TEMPLATES_PATH

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.post("/fragment")
async def client_instruction_fragment(user: UserCRUDRequest) -> UserInstructionFragment:
    """Return user instructions, we use POST because the integration layer might not keep
    track of callsigns and certs by UUID and will probably need both for the instructions"""
    template = Environment(loader=FileSystemLoader(TEMPLATES_PATH), autoescape=True).get_template("clientinfo.html")
    result = UserInstructionFragment(html=template.render(**user.dict()))
    return result
