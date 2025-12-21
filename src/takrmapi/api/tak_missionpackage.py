"""Endpoint to deliver user missionpackages from templates/tak_missionpackage"""

from pathlib import Path
import logging
import base64
import binascii
import urllib
import time
import os
from typing import List, Dict
from cryptography.hazmat.primitives import hashes, padding
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
    """Work in progress... Return ephemeral download link to get TAK client zip file"""
    localuser = tak_helpers.UserCRUD(user)
    if not localuser:
        raise HTTPException(status_code=404, detail="User data not found")
    request_time = int(time.time())
    r_data: str = f"{user.callsign}__{user.uuid}__{variant}"

    padder = padding.PKCS7(128).padder()
    r_padded = padder.update(r_data.encode("ascii"))
    r_padded += padder.finalize()

    iv = os.urandom(16)
    key: str = TAKDataPackage.get_ephemeral_key()

    cipher = Cipher(algorithms.AES(key.encode("ascii")), modes.CBC(iv))
    encryptor = cipher.encryptor()

    ct_b64: str = base64.b64encode(encryptor.update(r_padded) + encryptor.finalize()).decode("ascii")

    pltime_hash: str = await hash_from_str(ct_b64 + str(iv) + str(request_time))

    urlsafe: str = urllib.parse.quote_plus(
        base64.b64encode("{}__{}__{}__{}".format(ct_b64, str(iv), request_time, pltime_hash).encode("ascii")).decode(
            "ascii"
        )
    )

    return {
        "ephemeral_url": "https://{}:{}/ephemeral/api/v1/tak-missionpackages/ephemeral-wip/{}".format(
            config.read_tak_fqdn(), config.PRODUCT_HTTPS_EPHEMERAL_PORT, urlsafe
        )
    }


@ephemeral_router.get("/ephemeral-wip/{ephemeral_str}")
# async def wip_return_ephemeral_tak_zip(ephemeral_str: str, background_tasks: BackgroundTasks) -> Dict[str, str]:
async def wip_return_ephemeral_tak_zip(ephemeral_str: str) -> Dict[str, str]:
    """Work in progres... Return the TAK client zip file using ephemeral link"""
    try:
        e_decoded = base64.b64decode(ephemeral_str.encode("ascii")).decode("ascii")
    except binascii.Error as exc:
        LOGGER.info("Unable to decode base64 to string... Possible malformed query...")
        LOGGER.debug(exc)
        raise HTTPException(status_code=404, detail="User data not found") from exc
    e_split: List[str] = e_decoded.split("__")

    # payload: bytes = e_split[0].encode("ascii")
    payload_str: str = e_split[0]
    payload_decoded = base64.b64decode(payload_str.encode("ascii"))

    iv_str = e_split[1]
    iv: bytes = e_split[1].encode("ascii")
    request_time: int = int(e_split[2])
    digest_str: str = e_split[3]

    if request_time + 300 < int(time.time()):
        raise HTTPException(status_code=404, detail="User data not found")

    pltime_hash: str = await hash_from_str(payload_str + iv_str + str(request_time))

    if pltime_hash != digest_str:
        LOGGER.info("Checksum mismatch. Calculated: {} but got from response: {}".format(pltime_hash, digest_str))
        raise HTTPException(status_code=404, detail="User data not found")

    # unpadder = padding.PKCS7(128).unpadder()
    # data = unpadder.update(payload_decoded)
    # data += unpadder.finalize()

    key: str = TAKDataPackage.get_ephemeral_key()
    cipher = Cipher(algorithms.AES(key.encode("ascii")), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypt_data = decryptor.update(payload_decoded) + decryptor.finalize()
    LOGGER.debug(decrypt_data)

    return {"asd": "TODO"}
