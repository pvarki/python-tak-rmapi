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

from takrmapi import tak_helpers, config

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.get("/assets/{file_path:path}")
async def get_asset(file_path: str) -> FileResponse:
    """Asset file"""
    basepath = Path("/opt/templates/rune/assets")
    assetpath = basepath / file_path
    if not assetpath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(assetpath))


@router.post("/{language}")
async def user_intructions(user: UserCRUDRequest, language: str) -> Dict[str, str]:
    """return user instructions"""
    LOGGER.debug("Called")

    localuser = tak_helpers.UserCRUD(user)

    # Check user data path exists.
    if not localuser.userdata.exists():
        LOGGER.warning("No userdata found, trying to create")
        task = asyncio.create_task(localuser.add_new_user())
        await asyncio.shield(task)

    instructions_json_file = Path("/opt/templates/rune/tak.json")
    rune_text = instructions_json_file.read_text(encoding="utf-8")
    manifest = config.load_manifest()
    rune_text = rune_text.replace("__TAKAPI_ASSETS_BASE__", f"{manifest['product']['api']}api/v1/instructions/assets")
    tak_instructions_data = json.loads(rune_text)
    LOGGER.debug("RUNE JSON loaded")

    LOGGER.debug("Getting zip files")
    tak_missionpkg = tak_helpers.MissionZip(localuser)
    zip_base = Path(config.TAK_MISSIONPKG_TEMPLATES_FOLDER)
    zip_folders = [zip_base / "atak", zip_base / "itak", zip_base / "tak-tracker"]
    zip_files, tmp_folder = await tak_missionpkg.create_zip_bundles(zip_folders, is_mission_package=True)
    LOGGER.debug("Got {}".format(zip_files))

    # FIXME: Replace with links to /api/v1/tak-datapackages/clientzip/variant.zip
    for filestr in zip_files:
        file = Path(filestr)
        LOGGER.debug("Embedding {}".format(file))
        tak_instructions_data.append(
            {
                "type": "Asset",
                "name": file.name,
                "body": f"data:application/zip;base64,{base64.b64encode(file.read_bytes()).decode('ascii')}",
            }
        )

    LOGGER.debug("Removing {}".format(tmp_folder))
    await tak_missionpkg.helpers.remove_tmp_dir(str(tmp_folder))
    LOGGER.debug("Retuning")

    return {"callsign": user.callsign, "instructions": json.dumps(tak_instructions_data), "language": language}
