""" router.py: API router. """
from fastapi.routing import APIRouter

from takrmapi.web.api import (
    healthcheck,
    config,
    cmd,
    release,
)


api_router = APIRouter()
api_router.include_router(healthcheck.router, prefix="/healthcheck", tags=["healthcheck"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(cmd.router, prefix="/cmd", tags=["cmd"])
api_router.include_router(release.router, prefix="/release", tags=["release"])
