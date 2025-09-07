"""Endpoint to deliver files/templates from templates/tak_datapackage"""

from pathlib import Path
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import tak_helpers

from ..config import TAK_DATAPACKAGE_TEMPLATES_FOLDER

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.get("/{package_path:path}", response_class=FileResponse)
async def return_datapackage_file(package_path: str) -> FileResponse:
    # async def return_datapackage_file(user: UserCRUDRequest, package_path: str) -> FileResponse:
    """Return file from tak_datapackages. If file ends with .tpl, return rendered file"""

    # TODO is there need for user specific stuff? Need to find out how to get the userCrud...
    user: tak_helpers.UserCRUD = tak_helpers.UserCRUD(
        UserCRUDRequest(uuid="todo_fix_proper_user", callsign="todo_fix_proper_user", x509cert="todo_fix_proper_user")
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
