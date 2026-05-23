"""MediaMTX -> TAK video sync helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence, cast
import asyncio
import hashlib
import logging
import ssl

import aiohttp
from libpvarki.mtlshelp.context import get_ca_context
from libpvarki.schemas.product import UserCRUDRequest

from takrmapi import config
from takrmapi.takutils.tak_helpers import UserCRUD
from takrmapi.takutils.tak_rest_helpers import RestHelpers

LOGGER = logging.getLogger(__name__)
MANAGED_VIDEO_PREFIX = "rmmtx"


class StreamSyncError(RuntimeError):
    """Sync input/output is invalid."""


@dataclass(frozen=True)
class VideoSyncPlan:
    """Planned TAK mutations for a sync pass."""

    create: list[dict[str, Any]]
    update: list[dict[str, Any]]
    delete: list[str]


def managed_uid_prefix(deployment: str | None = None) -> str:
    """Return the TAK uid prefix reserved for this sync worker."""
    deployment_name = deployment or config.read_deployment_name()
    return f"{MANAGED_VIDEO_PREFIX}-{deployment_name}-"


def managed_video_uuid(path: str, deployment: str | None = None) -> str:
    """Return a deterministic TAK uuid for a MediaMTX path."""
    deployment_name = deployment or config.read_deployment_name()
    digest = hashlib.sha256(f"{deployment_name}:{path}".encode("utf-8")).hexdigest()[:16]
    return f"{managed_uid_prefix(deployment_name)}{digest}"


def _normalize_uuid(payload: Mapping[str, Any]) -> str:
    """Get uuid/uid from TAK payloads."""
    uuid = payload.get("uuid", payload.get("uid", ""))
    return str(uuid)


def build_video_connection(stream: Mapping[str, Any]) -> dict[str, Any]:
    """Build a TAK VideoConnection payload from a TAK-facing stream inventory item."""
    path = str(stream["path"])
    alias = str(stream.get("alias") or path.lstrip("/"))
    urls = stream.get("urls", {})
    if not isinstance(urls, Mapping) or not urls.get("rtmps"):
        raise StreamSyncError(f"Stream '{path}' does not include an RTMPS URL")
    video_uuid = managed_video_uuid(path)
    feed_uuid = f"{video_uuid}-feed0"
    return {
        "uuid": video_uuid,
        "active": True,
        "alias": alias,
        "thumbnail": "",
        "classification": config.TAK_VIDEO_CLASSIFICATION,
        "feeds": [
            {
                "uuid": feed_uuid,
                "active": True,
                "alias": alias,
                "url": str(urls["rtmps"]),
                "order": 0,
            }
        ],
    }


def _normalized_feed(feed: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a TAK feed payload for comparisons."""
    return {
        "uuid": _normalize_uuid(feed),
        "active": bool(feed.get("active", True)),
        "alias": str(feed.get("alias", "")),
        "url": str(feed.get("url", "")),
        "order": int(feed.get("order", 0) or 0),
    }


def normalized_video_connection(video: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a TAK video connection payload for comparisons."""
    feeds = [_normalized_feed(feed) for feed in cast(Sequence[Mapping[str, Any]], video.get("feeds", []))]
    feeds.sort(key=lambda item: item["uuid"])
    return {
        "uuid": _normalize_uuid(video),
        "active": bool(video.get("active", True)),
        "alias": str(video.get("alias", "")),
        "thumbnail": str(video.get("thumbnail", "")),
        "classification": str(video.get("classification", "")),
        "feeds": feeds,
    }


def plan_video_sync(
    desired_streams: Sequence[Mapping[str, Any]],
    existing_video_connections: Sequence[Mapping[str, Any]],
) -> VideoSyncPlan:
    """Compute TAK create/update/delete operations for managed video connections."""
    desired = {item["uuid"]: item for item in [build_video_connection(stream) for stream in desired_streams]}
    existing = {_normalize_uuid(video): video for video in existing_video_connections if _normalize_uuid(video)}

    create = [payload for uuid, payload in desired.items() if uuid not in existing]
    update = [
        payload
        for uuid, payload in desired.items()
        if uuid in existing and normalized_video_connection(existing[uuid]) != normalized_video_connection(payload)
    ]
    delete = [uuid for uuid in existing if uuid.startswith(managed_uid_prefix()) and uuid not in desired]
    delete.sort()
    return VideoSyncPlan(create=create, update=update, delete=delete)


def read_product_cert_pem() -> str:
    """Read the product certificate used for RM product interop."""
    if not config.RM_PRODUCT_CERT_PATH.exists():
        raise FileNotFoundError(f"Product certificate not found: {config.RM_PRODUCT_CERT_PATH}")
    return config.RM_PRODUCT_CERT_PATH.read_text(encoding="utf-8")


def build_interop_request() -> dict[str, str]:
    """Build RM interop registration payload for takrmapi."""
    cert_pem = read_product_cert_pem().rstrip() + "\n"
    return {
        "certcn": config.read_product_certcn(),
        "x509cert": cert_pem.replace("\n", "\\n"),
    }


class MediaMTXTakSync:
    """Periodic MediaMTX -> TAK synchronizer."""

    def __init__(self, rest_helper: RestHelpers | None = None) -> None:
        """Initialize sync helper."""
        user = UserCRUD(UserCRUDRequest(uuid="not_needed", callsign="mtlsclient", x509cert="not_needed"))
        self.rest_helper = rest_helper or RestHelpers(user)

    def rm_product_ssl_context(self) -> ssl.SSLContext:
        """Build SSL context for RM product mTLS."""
        cadir = Path("/ca_public")
        if not cadir.is_dir():
            raise FileNotFoundError(f"RM product CA directory not found: {cadir}")
        sslcontext = get_ca_context(ssl.Purpose.SERVER_AUTH, cadir)
        sslcontext.load_cert_chain(config.RM_PRODUCT_CERT_PATH, config.RM_PRODUCT_KEY_PATH)
        return sslcontext

    def product_api_connector(self) -> aiohttp.TCPConnector:
        """Build TLS connector for product API calls."""
        return aiohttp.TCPConnector(ssl=self.rm_product_ssl_context())

    def rm_product_session(self) -> aiohttp.ClientSession:
        """Create a product-authenticated session to RM API."""
        return aiohttp.ClientSession(
            base_url=config.RM_API_MTLS_BASE_URL,
            connector=aiohttp.TCPConnector(ssl=self.rm_product_ssl_context()),
            raise_for_status=True,
        )

    async def ensure_interop(self) -> None:
        """Ensure takrmapi is registered for interop with rmmtxauthz via RM API."""
        async with self.rm_product_session() as session:
            resp = await session.post(
                f"/api/v1/product/interop/{config.MTX_PRODUCT_NAME}", json=build_interop_request()
            )
            payload = await resp.json(content_type=None)
            if resp.status != 200 or not payload.get("success"):
                raise StreamSyncError(f"RM interop registration failed: {payload}")

    async def fetch_authz(self) -> Mapping[str, Any]:
        """Fetch brokered product authz from RM API."""
        async with self.rm_product_session() as session:
            resp = await session.get(f"/api/v1/product/interop/{config.MTX_PRODUCT_NAME}/authz")
            payload = await resp.json(content_type=None)
            if resp.status != 200:
                raise StreamSyncError(f"RM authz fetch failed: {payload}")
            if payload.get("type") != "basic" or not payload.get("username") or not payload.get("password"):
                raise StreamSyncError(f"Unsupported authz payload: {payload}")
            return payload

    async def fetch_streams(self, authz: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
        """Fetch TAK-facing active stream inventory from rmmtxauthz."""
        auth = aiohttp.BasicAuth(login=str(authz["username"]), password=str(authz["password"]))
        async with aiohttp.ClientSession(
            base_url=config.MTX_PRODUCT_API_BASE_URL,
            auth=auth,
            connector=self.product_api_connector(),
            raise_for_status=True,
        ) as session:
            resp = await session.get(config.MTX_INTEROP_STREAMS_PATH)
            payload = await resp.json(content_type=None)
            if resp.status != 200 or not isinstance(payload, list):
                raise StreamSyncError(f"Invalid stream inventory payload: {payload}")
            return payload

    async def run_once(self) -> VideoSyncPlan:
        """Run one sync pass."""
        await self.ensure_interop()
        authz = await self.fetch_authz()
        desired_streams = await self.fetch_streams(authz)

        existing_resp = await self.rest_helper.tak_api_video_list()
        if not existing_resp["success"]:
            raise StreamSyncError(f"Unable to fetch TAK video connections: {existing_resp['data']}")
        existing_connections = cast(
            Sequence[Mapping[str, Any]],
            cast(Mapping[str, Any], existing_resp["data"]).get("videoConnections", []),
        )

        plan = plan_video_sync(desired_streams, existing_connections)
        if plan.create:
            create_resp = await self.rest_helper.tak_api_video_create({"videoConnections": plan.create})
            if not create_resp["success"]:
                raise StreamSyncError(f"Unable to create TAK video connections: {create_resp['data']}")
        for payload in plan.update:
            update_resp = await self.rest_helper.tak_api_video_update(str(payload["uuid"]), payload)
            if not update_resp["success"]:
                raise StreamSyncError(
                    f"Unable to update TAK video connection '{payload['uuid']}': {update_resp['data']}"
                )
        for uuid in plan.delete:
            delete_resp = await self.rest_helper.tak_api_video_delete(uuid)
            if not delete_resp["success"]:
                raise StreamSyncError(f"Unable to delete TAK video connection '{uuid}': {delete_resp['data']}")
        return plan

    async def run_forever(self) -> None:
        """Run sync periodically until cancelled."""
        while True:
            try:
                plan = await self.run_once()
                LOGGER.info(
                    "MediaMTX sync pass complete (create=%s update=%s delete=%s)",
                    len(plan.create),
                    len(plan.update),
                    len(plan.delete),
                )
            except asyncio.CancelledError:
                raise
            except (StreamSyncError, aiohttp.ClientError, OSError, ssl.SSLError, ValueError) as exc:
                LOGGER.exception("MediaMTX sync pass failed: %s", exc)
            await asyncio.sleep(config.STREAM_SYNC_INTERVAL)
