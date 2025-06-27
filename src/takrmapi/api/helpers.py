"""General helpers"""

from fastapi import Request, HTTPException

from .. import config


def comes_from_rm(request: Request) -> None:
    """Check the CN, raises 403 if not"""
    payload = request.state.mtlsdn
    if payload.get("CN") != config.RMCN:
        raise HTTPException(status_code=403)
