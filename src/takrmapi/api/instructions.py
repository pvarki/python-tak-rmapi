"""Instructions endpoints"""

from typing import Dict
import logging
import json
import base64
import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import tak_helpers

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.post("/{language}")
async def user_intructions(user: UserCRUDRequest, language: str) -> Dict[str, str]:
    """return user instructions"""

    localuser = tak_helpers.UserCRUD(user)

    # Check user data path exists.
    if not localuser.userdata.exists():
        await asyncio.sleep(0.1)
        raise HTTPException(status_code=404, detail="User not available or userdata path not populated yet.")

    instructions_json_file = Path(f"/opt/templates/tak_{language}.json")
    if not instructions_json_file.is_file():
        instructions_json_file = Path("/opt/templates/tak.json")

    tak_instructions_data = json.loads(instructions_json_file.read_text(encoding="utf-8"))

    
    tak_missionpkg = tak_helpers.MissionZip(localuser)
    zip_files, tmp_folder = await tak_missionpkg.create_missionpkg()

    for file in zip_files:
        with open(file, "rb") as filehandle:
            contents = filehandle.read()
        filename = file.split("/")[-1]

        tak_instructions_data.append(
            {
                "type": "Asset",
                "name": filename,
                "body": f"data:application/zip;base64,{base64.b64encode(contents).decode('ascii')}",
            }
        )

    await tak_missionpkg.helpers.remove_tmp_dir(str(tmp_folder))

    return {"callsign": user.callsign, "instructions": json.dumps(tak_instructions_data), "language": language}
