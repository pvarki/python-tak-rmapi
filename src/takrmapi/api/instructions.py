"""Instructions endpoints"""

from typing import Dict
import logging
import json
import base64
from typing import List, Dict

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
    with open('/opt/templates/tak.json', 'r', encoding="utf-8") as file:
        data = json.load(file)

    localuser = tak_helpers.UserCRUD(user)
    tak_missionpkg = tak_helpers.MissionZip(localuser)
    zip_files = await tak_missionpkg.create_missionpkg()
    for file in zip_files:
        with open(file, "rb") as filehandle:
            contents = filehandle.read()
        filename = file.split("/")[-1]
        data.append(
            {
                "type": "Asset",
                "name": f"{filename}",
                "body": f"data:application/zip;base64,{base64.b64encode(contents).decode('ascii')}",
            }
        )

    return {
        "callsign": user.callsign,
        "instructions": json.dumps(data),
        "language": "en"
    }
