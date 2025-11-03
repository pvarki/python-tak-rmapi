"""Endpoints for information for the end-user"""

import logging
import base64
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest
from .schemas import ClientInstructionData, ClientInstructionResponse

from takrmapi import tak_helpers
from ..config import TAK_MISSIONPKG_ENABLED_PACKAGES

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.post("/data", response_model=ClientInstructionResponse)
async def client_instruction_fragment(user: UserCRUDRequest) -> ClientInstructionResponse:
    """Return zip package containing client config and certificates"""
    localuser = tak_helpers.UserCRUD(user)
    tak_missionpkg = tak_helpers.MissionZip(localuser)
    zip_files, tmp_folder = await tak_missionpkg.create_zip_bundles(
        template_folders=TAK_MISSIONPKG_ENABLED_PACKAGES, is_mission_package=True
    )
    returnable = []

    for file in zip_files:
        contents = file.read_bytes()
        returnable.append(
            {
                "title": file.name,
                "filename": f"{user.callsign}_{file.name}",
                "data": f"data:application/zip;base64,{base64.b64encode(contents).decode('ascii')}",
            }
        )
    await tak_missionpkg.helpers.remove_tmp_dir(str(tmp_folder))

    return ClientInstructionResponse(data={"tak_zips": returnable})
