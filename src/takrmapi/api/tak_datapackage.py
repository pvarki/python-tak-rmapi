"""Endpoint to deliver files/templates from templates/tak_datapackage"""

from typing import List, Dict
from pathlib import Path
import base64
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import tak_helpers

from ..config import TAK_DATAPACKAGE_TEMPLATES_FOLDER

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.get("/package/{package_path:path}")
async def return_datapackage_zip(user: UserCRUDRequest, package_path: str) -> List[Dict[str, str]]:
    """Return zip package from folder contents under requested path, use folder name as package name"""
    localuser = tak_helpers.UserCRUD(user)
    tak_missionpkg = tak_helpers.MissionZip(localuser)

    folderpath = Path(TAK_DATAPACKAGE_TEMPLATES_FOLDER) / package_path

    # Check if the folder exists
    if not folderpath.is_dir():
        raise HTTPException(status_code=404, detail="Requested datapackage path not found")

    zip_files, tmp_folder = await tak_missionpkg.create_zip_bundles(
        template_folders=[folderpath], is_mission_package=False
    )

    returnable_files: List[Dict[str, str]] = []

    for file in zip_files:
        contents = file.read_bytes()
        returnable_files.append(
            {
                "title": file.name,
                "data": f"data:application/zip;base64,{base64.b64encode(contents).decode('ascii')}",
                "filename": f"{user.callsign}_{file.name}",
            }
        )
    await tak_missionpkg.helpers.remove_tmp_dir(str(tmp_folder))
    return returnable_files


@router.get("/file/{package_path:path}")
async def return_datapackage_file(user: UserCRUDRequest, package_path: str) -> Response:
    """Return file from tak_datapackages. If file ends with .tpl, return rendered file"""

    localuser = tak_helpers.UserCRUD(user)
    tak_missionpkg = tak_helpers.MissionZip(localuser)

    filepath = Path(TAK_DATAPACKAGE_TEMPLATES_FOLDER) / package_path

    # Check if the file exists
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="Requested datapackage file not found")

    filename = package_path.split("/")[-1]
    if filename.endswith(".tpl"):
        tak_missionpkg = tak_helpers.MissionZip(localuser)
        rendered_file_str = await tak_missionpkg.render_tak_manifest_template(Path(filepath))
        return Response(rendered_file_str.encode(encoding="utf-8"), media_type="text/plain")

    return FileResponse(filepath)
