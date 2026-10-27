"""Federation operations through TAK's REST controller and Ignite services."""

from __future__ import annotations

import asyncio
import re
import ssl
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import aiohttp
import filelock
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from fastapi import HTTPException

from takrmapi import config

from .tak_rest_helpers import RestHelpers

if TYPE_CHECKING:
    from takrmapi.api.federation_schemas import FederationRequest

MAX_CA_BYTES = 1024 * 1024


def intermediate_fingerprint(pem: bytes) -> str:
    """Require exactly one current intermediate CA before any TAK mutation."""
    if len(pem) >= MAX_CA_BYTES or not re.fullmatch(
        rb"\s*-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----\s*", pem
    ):
        raise ValueError("Expected exactly one PEM certificate smaller than 1 MiB")
    cert = x509.load_pem_x509_certificate(pem)
    now = datetime.now(UTC)
    if not cert.not_valid_before_utc <= now < cert.not_valid_after_utc:
        raise ValueError("CA certificate is not currently valid")
    if cert.subject == cert.issuer:
        raise ValueError("Expected an intermediate CA, not a root")
    try:
        if not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise ValueError("Certificate is not a CA")
    except x509.ExtensionNotFound as exc:
        raise ValueError("Missing CA basic constraints") from exc
    try:
        if not cert.extensions.get_extension_for_class(x509.KeyUsage).value.key_cert_sign:
            raise ValueError("CA key usage does not permit certificate signing")
    except x509.ExtensionNotFound:
        pass
    return cert.fingerprint(hashes.SHA256()).hex(":").upper()


async def download_intermediate(remote_base: str) -> bytes:
    """Use public HTTPS trust without local credentials, cookies or redirects."""
    async with (
        aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5), cookie_jar=aiohttp.DummyCookieJar(), trust_env=False
        ) as session,
        session.get(
            f"https://{remote_base}/ca/public/intermediate_ca.pem",
            ssl=ssl.create_default_context(),
            allow_redirects=False,
        ) as response,
    ):
        if response.status != 200:
            raise ValueError("Remote CA download did not return HTTP 200")
        pem = bytearray()
        async for chunk in response.content.iter_chunked(65536):
            pem.extend(chunk)
            if len(pem) >= MAX_CA_BYTES:
                raise ValueError("Remote CA certificate exceeds size limit")
        return bytes(pem)


# The lock lives on the shared TAK volume, so all service workers serialize writes.
OPERATION_SECONDS = 20
LOCK_SECONDS = 3


class FederationOperation:
    """One bounded, retryable local configuration operation."""

    def __init__(self, peer: FederationRequest) -> None:
        self.peer = peer
        self.rest = RestHelpers()
        self.stage = "fetch_ca"
        self.may_have_changed = False

    def error(self, status: int, code: str, message: str) -> HTTPException:
        """Only return public, fixed error messages."""
        return HTTPException(
            status_code=status,
            detail={"code": code, "stage": self.stage, "message": message, "may_have_changed": self.may_have_changed},
        )

    async def run(self) -> dict[str, Any]:
        """Include download, lock wait and all TAK requests in one deadline."""
        try:
            async with asyncio.timeout(OPERATION_SECONDS):
                pem = await download_intermediate(self.peer.remote_base)
                fingerprint = intermediate_fingerprint(pem)
                self.stage = "verify"
                lock = filelock.FileLock(config.TAK_CERTS_FOLDER / "federation.lock")
                until = asyncio.get_running_loop().time() + LOCK_SECONDS
                while True:
                    try:
                        # Nonblocking attempts keep cancellation and the event loop responsive.
                        lock.acquire(timeout=0)
                        break
                    except filelock.Timeout:
                        if asyncio.get_running_loop().time() >= until:
                            raise self.error(
                                503, "federation_busy", "Another federation operation holds the lock"
                            ) from None
                        await asyncio.sleep(0.05)
                try:
                    return await self.trust(pem, fingerprint)
                finally:
                    lock.release()
        except TimeoutError as exc:
            raise self.error(504, "federation_timeout", "Federation operation timed out") from exc
        except aiohttp.ClientResponseError as exc:
            if exc.status == 409:
                raise self.error(409, "tak_conflict", "TAK rejected a conflicting configuration") from exc
            raise self.error(502, "tak_error", "TAK request failed") from exc
        except (aiohttp.ClientError, ValueError, x509.DuplicateExtension) as exc:
            raise self.error(502, "federation_upstream_error", "Invalid CA or unexpected upstream response") from exc
        except OSError as exc:
            raise self.error(503, "federation_unavailable", "Local federation resources unavailable") from exc

    async def records(self, path: str) -> list[dict[str, Any]]:
        """Reject malformed lists before deciding whether a write is needed."""
        data = await self.rest.federation_request("GET", path)
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise ValueError("Expected a TAK record list")
        return cast(list[dict[str, Any]], data)

    async def has_ca(self, fingerprint: str) -> bool:
        """Match DER fingerprint, never the certificate name."""
        records = await self.records("federatecertificates")
        if any(not isinstance(item.get("fingerPrint"), str) for item in records):
            raise ValueError("Missing CA fingerprint")
        return any(item["fingerPrint"] == fingerprint for item in records)

    async def directions(self, fingerprint: str) -> set[str]:
        """BOTH is stored as separate INBOUND and OUTBOUND associations."""
        records = await self.records(f"federatecagroups/{fingerprint}")
        if any(
            item.get("caId") != fingerprint
            or not isinstance(item.get("group"), str)
            or item.get("direction") not in ("INBOUND", "OUTBOUND")
            for item in records
        ):
            raise ValueError("Malformed CA group association")
        return {item["direction"] for item in records if item["group"] == "default"}

    async def trust(self, pem: bytes, fingerprint: str) -> dict[str, Any]:
        """Add only missing trust and group directions, then verify visible state."""
        changed = False
        self.stage = "upload_ca"
        if not await self.has_ca(fingerprint):
            self.may_have_changed = True
            await self.rest.federation_request("POST", "federatecertificates", pem=pem)
            changed = True
        self.stage = "verify"
        if not await self.has_ca(fingerprint):
            raise self.error(502, "ca_readback_failed", "CA was not visible after upload")
        self.stage = "groups"
        missing = {"INBOUND", "OUTBOUND"} - await self.directions(fingerprint)
        if missing:
            self.may_have_changed = True
            await self.rest.federation_request(
                "POST",
                "federatecagroups",
                body={
                    "caId": fingerprint,
                    "group": "default",
                    "direction": "BOTH" if len(missing) == 2 else missing.pop(),
                },
            )
            changed = True
        self.stage = "verify"
        if await self.directions(fingerprint) != {"INBOUND", "OUTBOUND"}:
            raise self.error(502, "groups_readback_failed", "CA groups were not visible after update")
        return {"remote_base": self.peer.remote_base, "changed": changed, "ca_fingerprint": fingerprint}
