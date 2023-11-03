"""Endpoints for information for the end-user"""
import logging
import base64
from typing import List, Dict
from fastapi import APIRouter, Depends
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import tak_helpers

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.post("/fragment")
# async def get_missionpkg(user_mission: UserMissionZipRequest) -> List[Dict[str, str]]:
async def client_instruction_fragment(user: UserCRUDRequest) -> List[Dict[str, str]]:
    """Return zip package containing client config and certificates"""
    tak_missionpkg = tak_helpers.MissionZip(user)
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
                "filename": f"{user.callsign}_{filename}",
            }
        )
    return returnable
