""""factory for the fastpi app"""
import logging

from fastapi import FastAPI
from libpvarki.logging import init_logging

from takrmapi import __version__
from .config import LOG_LEVEL
from .api import all_routers

LOGGER = logging.getLogger(__name__)


def get_app() -> FastAPI:
    """Returns the FastAPI application."""

    init_logging(LOG_LEVEL)
    app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json", version=__version__)
    app.include_router(router=all_routers, prefix="/api/v1")

    LOGGER.info("API init done, setting log verbosity to '{}'.".format(logging.getLevelName(LOG_LEVEL)))

    return app
