"""Endpoint to deliver files/templates from templates/tak_datapackage"""

from typing import cast
from pathlib import Path
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, Response
from libpvarki.middleware.mtlsheader import MTLSHeader, DNDict
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import tak_helpers
from ..config import TAK_DATAPACKAGE_TEMPLATES_FOLDER

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.get("/package/{package_path:path}")
async def return_datapackage_zip(package_path: str, request: Request, background_tasks: BackgroundTasks) -> Response:
    """Return zip package from folder contents under requested path, use folder name as package name"""
    payload = cast(DNDict, request.state.mtlsdn)
    callsign: str = payload["CN"]
    user: tak_helpers.UserCRUD = tak_helpers.UserCRUD(UserCRUDRequest(uuid="NA", callsign=callsign, x509cert=""))
    pkg_helper = tak_helpers.MissionZip(user)

    folderpath = Path(TAK_DATAPACKAGE_TEMPLATES_FOLDER) / package_path

    # Check if the folder exists and no trailing "/"
    if not folderpath.is_dir() or package_path[-1] == "/":
        raise HTTPException(status_code=404, detail="Requested datapackage not found in given path")

    zip_files, tmp_folder = await pkg_helper.create_zip_bundles(template_folders=[folderpath], is_mission_package=False)

    # Remove/clear temp in background
    background_tasks.add_task(pkg_helper.helpers.remove_tmp_dir, tmp_folder)

    return FileResponse(zip_files[0])


@router.get("/file/{file_path:path}")
async def return_datapackage_file(file_path: str, request: Request) -> Response:
    """Return file from tak_datapackages. If file ends with .tpl, return rendered file"""
    payload = cast(DNDict, request.state.mtlsdn)
    callsign: str = payload["CN"]
    user: tak_helpers.UserCRUD = tak_helpers.UserCRUD(UserCRUDRequest(uuid="NA", callsign=callsign, x509cert=""))

    tak_missionpkg = tak_helpers.MissionZip(user)

    filepath = Path(TAK_DATAPACKAGE_TEMPLATES_FOLDER) / file_path

    # Check if the file exists
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="Requested datapackage file not found")

    filename = file_path.split("/")[-1]
    if filename.endswith(".tpl"):
        tak_missionpkg = tak_helpers.MissionZip(user)
        rendered_file_str = await tak_missionpkg.render_tak_manifest_template(Path(filepath))
        return Response(rendered_file_str.encode(encoding="utf-8"), media_type="text/plain")

    return FileResponse(filepath)
