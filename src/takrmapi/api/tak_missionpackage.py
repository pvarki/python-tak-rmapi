"""Endpoint to deliver user missionpackages from templates/tak_missionpackage"""

from pathlib import Path
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from libpvarki.middleware.mtlsheader import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import config
from takrmapi.takutils import tak_helpers
from takrmapi.takutils.tak_pkg_helpers import TAKDataPackage, TAKPackageZip

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.post("/client-zip/{variant}.zip")
async def return_tak_zip(user: UserCRUDRequest, variant: str, background_tasks: BackgroundTasks) -> FileResponse:
    """Return TAK client zip file"""

    localuser = tak_helpers.UserCRUD(user)
    if not localuser:
        raise HTTPException(status_code=404, detail="User data not found")

    walk_dir = Path(config.TAK_MISSIONPKG_TEMPLATES_FOLDER) / "default" / variant

    if not walk_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Variant '{variant}' not found")

    tak_missionpkg = TAKPackageZip(localuser)

    target_pkg = TAKDataPackage(template_path=walk_dir, template_type="mission")
    await tak_missionpkg.create_zip_bundles(datapackages=[target_pkg])

    if not target_pkg.zip_path or not target_pkg.zip_path.is_file():
        raise HTTPException(status_code=500, detail="Failed to generate ZIP")

    background_tasks.add_task(tak_missionpkg.helpers.remove_tmp_dir, target_pkg.zip_tmp_folder)

    return FileResponse(
        path=target_pkg.zip_path,
        media_type="application/zip",
        filename=f"{localuser.callsign}_{variant}.zip",
    )
