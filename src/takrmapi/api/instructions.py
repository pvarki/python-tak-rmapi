"""Instructions endpoints"""

from typing import Dict
import logging
import json
import base64
import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import tak_helpers

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.get("/assets/{file_path:path}")
async def get_asset(file_path: str) -> FileResponse:
    """Asset file"""
    basepath = Path("/opt/templates/assets")
    assetpath = basepath / file_path
    if not assetpath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(assetpath))


@router.post("/{language}")
async def user_intructions(user: UserCRUDRequest, language: str) -> Dict[str, str]:
    """return user instructions"""
    LOGGER.info("Called")

    localuser = tak_helpers.UserCRUD(user)

    # Check user data path exists.
    if not localuser.userdata.exists():
        LOGGER.warning("No userdata found, trying to create")
        task = asyncio.create_task(localuser.add_new_user())
        await asyncio.shield(task)

    instructions_json_file = Path("/opt/templates/tak.json")
    tak_instructions_data = json.loads(instructions_json_file.read_text(encoding="utf-8"))

    tak_missionpkg = tak_helpers.MissionZip(localuser)
    zip_files, tmp_folder = await tak_missionpkg.create_missionpkg()

    for file in zip_files:
        with open(file, "rb") as filehandle:
            contents = filehandle.read()
        filename = file.split("/")[-1]  # FIXME: use pathlib.Path

        tak_instructions_data.append(
            {
                "type": "Asset",
                "name": filename,
                "body": f"data:application/zip;base64,{base64.b64encode(contents).decode('ascii')}",
            }
        )

    await tak_missionpkg.helpers.remove_tmp_dir(str(tmp_folder))

    return {"callsign": user.callsign, "instructions": json.dumps(tak_instructions_data), "language": language}
