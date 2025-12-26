"""Endpoint to deliver user missionpackages from templates/tak_missionpackage"""

from pathlib import Path
import logging
import base64
import binascii
import urllib
import time
import os
import json
from typing import List, Dict
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from libpvarki.middleware.mtlsheader import MTLSHeader
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import config
from takrmapi.takutils import tak_helpers
from takrmapi.takutils.tak_pkg_helpers import TAKDataPackage, TAKPackageZip

LOGGER = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])

ephemeral_router = APIRouter()


async def hash_from_str(hash_from: str) -> str:
    """Return checksum string from given string"""
    ct_digest = hashes.Hash(hashes.SHA256())
    ct_digest.update(hash_from.encode("ascii"))
    ct_dig = ct_digest.finalize()
    try:
        ct_dig_str = binascii.hexlify(ct_dig).decode()
    except binascii.Error as e:
        LOGGER.info("Unable to convert digest bin to string... Possible malformed query...")
        LOGGER.debug(e)
        return "err"

    return ct_dig_str


@router.post("/client-zip/{variant}.zip")
async def return_tak_zip(user: UserCRUDRequest, variant: str, background_tasks: BackgroundTasks) -> FileResponse:
    """Return TAK client zip file proxied from rm api"""

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


@router.post("/ephemeral/{variant}.zip")
async def return_ephemeral_dl_link(user: UserCRUDRequest, variant: str) -> Dict[str, str]:
    """MVP. Replace with better one once it works... Return ephemeral download link to get TAK client zip file"""
    localuser = tak_helpers.UserCRUD(user)
    if not localuser:
        raise HTTPException(status_code=404, detail="User data not found")
    request_time = int(time.time())
    r_str: str = f"{user.callsign}__{user.uuid}__{variant}__{request_time}"
    u_str: str = base64.b64encode(r_str.encode("ascii")).decode("ascii")
    urlsafe: str = urllib.parse.quote_plus(u_str)

    return {
        "ephemeral_url": "https://{}:{}/ephemeral/api/v1/tak-missionpackages/ephemeral/{}".format(
            config.read_tak_fqdn(), config.PRODUCT_HTTPS_EPHEMERAL_PORT, urlsafe
        )
    }


@ephemeral_router.get("/ephemeral/{ephemeral_str}")
async def return_ephemeral_tak_zip(ephemeral_str: str, background_tasks: BackgroundTasks) -> FileResponse:
    """MVP. Replace with better one once it works... Return the TAK client zip file using ephemeral link"""
    if ephemeral_str == "":
        raise HTTPException(status_code=404, detail="No found..")

    try:
        e_decoded = base64.b64decode(ephemeral_str.encode("ascii")).decode("ascii")
    except binascii.Error as exc:
        LOGGER.info("Unable to decode base64 to string... Possible malformed query...")
        LOGGER.debug(exc)
        raise HTTPException(status_code=404, detail="User data not found") from exc

    e_split: List[str] = e_decoded.split("__")
    try:
        callsign: str = e_split[0]
        uuid_str: str = e_split[1]
        variant: str = e_split[2]
        request_time: int = int(e_split[3])
    except IndexError as exc:
        LOGGER.info("Unable to decode base64 to string... Possible malformed query...")
        LOGGER.debug(exc)
        raise HTTPException(status_code=404, detail="User data not found") from exc

    # Five minute window to use the ephemeral link
    if not request_time + 300 > int(time.time()):
        raise HTTPException(status_code=404, detail="User data not found")

    localuser: tak_helpers.UserCRUD = tak_helpers.UserCRUD(
        UserCRUDRequest(uuid=uuid_str, callsign=callsign, x509cert="")
    )
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


@router.post("/ephemeral-wip/{variant}.zip")
async def wip_return_ephemeral_dl_link(user: UserCRUDRequest, variant: str) -> Dict[str, str]:
    """Return ephemeral download link to get TAK client zip file"""
    localuser = tak_helpers.UserCRUD(user)
    if not localuser:
        raise HTTPException(status_code=404, detail="User data not found")
    request_time = int(time.time())
    plaintext_str: str = json.dumps({"callsign": user.callsign, "uuid": user.uuid, "variant": variant})
    iv = os.urandom(12)

    encryptor = Cipher(algorithms.AES(TAKDataPackage.get_ephemeral_byteskey()), modes.GCM(iv)).encryptor()

    user_payload: bytes = encryptor.update(plaintext_str.encode("ascii")) + encryptor.finalize()

    user_payload_b64: str = base64.b64encode(user_payload).decode("ascii")
    iv_b64: str = base64.b64encode(iv).decode("ascii")
    payload_digest: str = await hash_from_str(user_payload_b64 + iv_b64 + str(request_time))

    urlsafe: str = urllib.parse.quote_plus(
        base64.b64encode(
            json.dumps(
                {
                    "payload_b64": user_payload_b64,
                    "iv_b64": iv_b64,
                    "request_time": request_time,
                    "digest": payload_digest,
                }
            ).encode("ascii")
        )
    )

    return {
        "ephemeral_url": "https://{}:{}/ephemeral/api/v1/tak-missionpackages/ephemeral-wip/{}".format(
            config.read_tak_fqdn(), config.PRODUCT_HTTPS_EPHEMERAL_PORT, urlsafe
        )
    }


@ephemeral_router.get("/ephemeral-wip/{ephemeral_str}")
async def wip_return_ephemeral_tak_zip(ephemeral_str: str, background_tasks: BackgroundTasks) -> FileResponse:
    # async def wip_return_ephemeral_tak_zip(ephemeral_str: str) -> Dict[str, str]:
    """Return the TAK client zip file using ephemeral link"""
    try:
        e_decoded = base64.b64decode(ephemeral_str.encode("ascii")).decode("ascii")
    except binascii.Error as exc:
        LOGGER.info("Unable to decode base64 to string... Possible malformed query...")
        LOGGER.debug(exc)
        raise HTTPException(status_code=404, detail="User data not found") from exc

    ephemeral_json = json.loads(e_decoded)

    if ephemeral_json["request_time"] + 300 < int(time.time()):
        raise HTTPException(status_code=404, detail="User data not found")

    payload_digest: str = await hash_from_str(
        ephemeral_json["payload_b64"] + ephemeral_json["iv_b64"] + str(ephemeral_json["request_time"])
    )

    if payload_digest != ephemeral_json["digest"]:
        LOGGER.info(
            "Checksum mismatch. Calculated: {} but got from response: {}".format(
                payload_digest, ephemeral_json["digest"]
            )
        )
        raise HTTPException(status_code=404, detail="User data not found")

    iv: bytes = base64.b64decode(ephemeral_json["iv_b64"].encode("ascii"))
    user_payload: bytes = base64.b64decode(ephemeral_json["payload_b64"].encode("ascii"))

    decryptor = Cipher(algorithms.AES(TAKDataPackage.get_ephemeral_byteskey()), modes.GCM(iv)).encryptor()

    decrypted_payload = decryptor.update(user_payload) + decryptor.finalize()
    decrypted_json = json.loads(decrypted_payload.decode("ascii"))

    LOGGER.debug("Got the following data in ephemeral user payload: {}".format(decrypted_json))

    localuser: tak_helpers.UserCRUD = tak_helpers.UserCRUD(
        UserCRUDRequest(uuid=decrypted_json["uuid"], callsign=decrypted_json["callsign"], x509cert="")
    )
    if not localuser:
        raise HTTPException(status_code=404, detail="User data not found")

    walk_dir = Path(config.TAK_MISSIONPKG_TEMPLATES_FOLDER) / "default" / decrypted_json["variant"]

    if not walk_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Variant '{decrypted_json['variant']}' not found")

    tak_missionpkg = TAKPackageZip(localuser)

    target_pkg = TAKDataPackage(template_path=walk_dir, template_type="mission")
    await tak_missionpkg.create_zip_bundles(datapackages=[target_pkg])

    if not target_pkg.zip_path or not target_pkg.zip_path.is_file():
        raise HTTPException(status_code=500, detail="Failed to generate ZIP")

    background_tasks.add_task(tak_missionpkg.helpers.remove_tmp_dir, target_pkg.zip_tmp_folder)

    return FileResponse(
        path=target_pkg.zip_path,
        media_type="application/zip",
        filename=f"{localuser.callsign}_{decrypted_json['variant']}.zip",
    )
