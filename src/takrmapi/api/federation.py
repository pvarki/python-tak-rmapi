"""Internal federation requests: only RMAPI itself may call these routes."""

from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from libpvarki.middleware import MTLSHeader

from takrmapi import config
from takrmapi.takutils.federation import FederationOperation

from .federation_schemas import FederationOutgoingResponse, FederationRequest, FederationTrustResponse
from .usercrud import comes_from_rm

router = APIRouter(dependencies=[Depends(MTLSHeader(auto_error=True))])


def check_local_peer(peer: FederationRequest) -> None:
    """Manifest identity, rather than the request Host header, prevents self-federation."""
    local = urlsplit(config.load_manifest()["rasenmaeher"]["init"]["base_uri"]).hostname
    if local is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "local_identity_unavailable",
                "stage": "authorize",
                "message": "Local deployment identity unavailable",
                "may_have_changed": False,
            },
        )
    if peer.hostname == local.lower():
        raise HTTPException(
            status_code=422,
            detail={
                "code": "self_federation",
                "stage": "authorize",
                "message": "Cannot federate with the local deployment",
                "may_have_changed": False,
            },
        )


@router.post("/trust")
async def trust(peer: FederationRequest, request: Request) -> FederationTrustResponse:
    """Ensure the remote intermediate CA and default groups exist locally."""
    comes_from_rm(request)
    check_local_peer(peer)
    return FederationTrustResponse(**await FederationOperation(peer).run())


@router.post("/outgoing")
async def outgoing(peer: FederationRequest, request: Request) -> FederationOutgoingResponse:
    """Ensure one local outgoing connection; the caller selects the initiating server."""
    comes_from_rm(request)
    check_local_peer(peer)
    return FederationOutgoingResponse(**await FederationOperation(peer).run(outgoing=True))
