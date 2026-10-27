"""Exercise actual HTTP requests and multipart encoding against a local TAK double."""

from unittest.mock import AsyncMock

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer
import pytest

from takrmapi.takutils.tak_rest_helpers import RestHelpers


@pytest.mark.asyncio
async def test_rest_wire_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = []

    async def handler(request: web.Request) -> web.Response:
        seen.append((request.method, request.path))
        if request.method == "POST" and request.path.endswith("federatecertificates"):
            field = await (await request.multipart()).next()
            assert field.name == "file"
            assert field.filename == "intermediate_ca.pem"
            assert await field.read() == b"certificate"
            return web.Response()
        if request.method == "POST":
            assert await request.json() == {"caId": "fingerprint", "group": "default", "direction": "BOTH"}
            return web.Response()
        return web.json_response({"data": []})

    app = web.Application()
    app.router.add_route("*", "/Marti/api/{path:.*}", handler)
    async with TestServer(app) as server:
        rest = RestHelpers()
        monkeypatch.setattr(rest.helpers, "tak_base_url", lambda: str(server.make_url("")).rstrip("/"))

        async def client() -> aiohttp.ClientSession:
            return aiohttp.ClientSession()

        monkeypatch.setattr(rest.helpers, "tak_mtls_client", client)
        monkeypatch.setattr(rest.helpers, "tak_mtls_client_sslcontext", AsyncMock(return_value=None))
        assert await rest.federation_request("GET", "federatecertificates") == []
        await rest.federation_request("POST", "federatecertificates", pem=b"certificate")
        await rest.federation_request(
            "POST", "federatecagroups", body={"caId": "fingerprint", "group": "default", "direction": "BOTH"}
        )
    assert seen == [
        ("GET", "/Marti/api/federatecertificates"),
        ("POST", "/Marti/api/federatecertificates"),
        ("POST", "/Marti/api/federatecagroups"),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("status,body", [(200, "{}"), (200, "not JSON"), (302, "redirect"), (403, "denied")])
async def test_rest_failure(monkeypatch: pytest.MonkeyPatch, status: int, body: str) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=status, text=body)

    app = web.Application()
    app.router.add_get("/Marti/api/test", handler)
    async with TestServer(app) as server:
        rest = RestHelpers()
        monkeypatch.setattr(rest.helpers, "tak_base_url", lambda: str(server.make_url("")).rstrip("/"))

        async def client() -> aiohttp.ClientSession:
            return aiohttp.ClientSession()

        monkeypatch.setattr(rest.helpers, "tak_mtls_client", client)
        monkeypatch.setattr(rest.helpers, "tak_mtls_client_sslcontext", AsyncMock(return_value=None))
        with pytest.raises((ValueError, aiohttp.ClientResponseError)):
            await rest.federation_request("GET", "test")
