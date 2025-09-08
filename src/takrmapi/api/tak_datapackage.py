"""Endpoint to deliver files/templates from templates/tak_datapackage"""

from pathlib import Path
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import tak_helpers, config

from ..config import TAK_DATAPACKAGE_TEMPLATES_FOLDER

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.get("/clientzip/{variant}.zip")
async def return_tak_zip(request: Request, variant: str) -> FileResponse:
    """Return TAK client zip as file"""
    certdn = request.state.mtlsdn
    user = tak_helpers.UserCRUD.from_callsign(certdn["CN"])
    if not user:
        raise HTTPException(status_code=404, detail="User data not found")
    zip_tmp_path = user.userdata / "ziptmp" / variant
    zip_tmp_path.mkdir(exist_ok=True, parents=True)
    mhelper = tak_helpers.MissionZip(user)
    walk_dir = Path(config.TAK_MISSIONPKG_TEMPLATES_FOLDER) / variant
    if not walk_dir.is_dir():
        raise HTTPException(status_code=404, detail="Variant not found")
    zipfile = await mhelper.create_mission_zip(zip_tmp_path, walk_dir, is_mission_package=True)
    return FileResponse(path=zipfile)


@router.get("/{package_path:path}", response_class=FileResponse)
async def return_datapackage_file(request: Request, package_path: str) -> FileResponse:
    # async def return_datapackage_file(user: UserCRUDRequest, package_path: str) -> FileResponse:
    """Return file from tak_datapackages. If file ends with .tpl, return rendered file"""
    certdn = request.state.mtlsdn
    user = tak_helpers.UserCRUD.from_callsign(certdn["CN"])
    if not user:
        LOGGER.warning("Could not resolve user, faking one since this route does not use specific data")
        user = tak_helpers.UserCRUD(
            UserCRUDRequest(uuid="invalid_user", callsign="invalid_user", x509cert="invalid_user")
        )

    filepath = Path(TAK_DATAPACKAGE_TEMPLATES_FOLDER) / package_path

    # Check if the file exists
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="Requested datapackage file not found")

    # Return
    filename = package_path.split("/")[-1]
    if filename.endswith(".tpl"):
        tak_missionpkg = tak_helpers.MissionZip(user)
        rendered_file = await tak_missionpkg.render_tak_manifest_template(Path(filepath))

        return FileResponse(rendered_file, filename=rendered_file.name)

    return FileResponse(filepath)
