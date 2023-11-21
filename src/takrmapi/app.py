""""factory for the fastpi app"""
from typing import AsyncGenerator
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from libpvarki.logging import init_logging

from takrmapi import __version__
from takrmapi import tak_init
from .config import LOG_LEVEL
from .api import all_routers


LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle lifespan management things"""
    # init
    await tak_init.setup_tak_mgmt_conn()
    _ = app
    # App runs
    yield
    # Cleanup


def get_app_no_init() -> FastAPI:
    """App init with lifespan"""
    app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=app_lifespan, version=__version__)
    app.include_router(router=all_routers, prefix="/api/v1")

    return app


def get_app() -> FastAPI:
    """Returns the FastAPI application."""
    init_logging(LOG_LEVEL)
    app = get_app_no_init()
    LOGGER.info("API init done, setting log verbosity to '{}'.".format(logging.getLevelName(LOG_LEVEL)))
    return app
