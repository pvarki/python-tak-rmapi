"""Instructions endpoints"""

from typing import Dict
import logging
import json
import base64
from pathlib import Path

from fastapi import APIRouter, Depends
from libpvarki.middleware import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import tak_helpers

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


@router.post("/{language}")
async def user_intructions(user: UserCRUDRequest) -> Dict[str, str]:
    """return user instructions"""

    # TODO load to memory on load,
    # instruction_content: str = Path("/opt/templates/tak.json").read_text(encoding="utf-8")
    tak_instructions_data = json.loads(Path("/opt/templates/tak.json").read_text(encoding="utf-8"))

    localuser = tak_helpers.UserCRUD(user)
    tak_missionpkg = tak_helpers.MissionZip(localuser)
    zip_files: list[Path] = await tak_missionpkg.create_missionpkg()

    for file in zip_files:
        contents = file.read_bytes()
        tak_instructions_data.append(
            {
                "type": "Asset",
                "name": f"{file.name}",
                "body": f"data:application/zip;base64,{base64.b64encode(contents).decode('ascii')}",
            }
        )

    return {"callsign": user.callsign, "instructions": json.dumps(tak_instructions_data), "language": "en"}
