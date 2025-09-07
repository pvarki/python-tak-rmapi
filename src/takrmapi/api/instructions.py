"""Instructions endpoints"""

from typing import Dict
import logging
import json
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


# FIXME: refactor to smaller methods
@router.post("/{language}")
async def user_intructions(user: UserCRUDRequest, language: str) -> Dict[str, str]:  # pylint: disable=R0914
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

    # FIXME: Check the asset type and body for non-embedded assets, this is a best guess
    for pkgpath in Path(config.TAK_MISSIONPKG_TEMPLATES_FOLDER).glob("*"):
        fname = f"{pkgpath.name}.zip"
        url = f"{manifest['product']['api']}api/v1/tak-datapackages/clientzip/{fname}"
        tak_instructions_data.append(
            {
                "type": "LinkAsset",
                "name": fname,
                "body": url,
            }
        )

    return {"callsign": user.callsign, "instructions": json.dumps(tak_instructions_data), "language": language}
