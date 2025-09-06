"""Endpoints for information for the end-user"""

import logging
import base64
from typing import List, Dict
from fastapi import APIRouter, Depends
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import tak_helpers
from ..config import TAK_MISSIONPKG_ENABLED_PACKAGES

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.post("/fragment", deprecated=True)
# async def get_missionpkg(user_mission: UserMissionZipRequest) -> List[Dict[str, str]]:
async def client_instruction_fragment(user: UserCRUDRequest) -> List[Dict[str, str]]:
    """Return zip package containing client config and certificates"""
    localuser = tak_helpers.UserCRUD(user)
    tak_missionpkg = tak_helpers.MissionZip(localuser)
    zip_files, tmp_folder = await tak_missionpkg.create_zip_bundles(
        template_folders = TAK_MISSIONPKG_ENABLED_PACKAGES,
        is_mission_package = True
    )
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
    await tak_missionpkg.helpers.remove_tmp_dir(str(tmp_folder))
    return returnable
