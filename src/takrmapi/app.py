""" "factory for the fastpi app"""

import asyncio
import random
from typing import AsyncGenerator
import logging
from contextlib import asynccontextmanager
import filelock

from fastapi import FastAPI
from libpvarki.logging import init_logging, add_trace_and_audit

from . import __version__
from . import config
from .takutils import tak_init
from .takutils import ignite_jni
from .config import LOG_LEVEL
from .api import all_routers, all_routers_v2, all_routers_ephemeral_v1


LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle lifespan management things"""
    # init

    lockpath = config.TAK_CERTS_FOLDER / "takrmapi_init.lock"
    # Random sleep to the lock file access to avoid race conditions
    await asyncio.sleep(random.random() / 2)  # nosec
    lock = filelock.FileLock(lockpath)

    try:
        lock.acquire(timeout=0.0)
        LOGGER.info("Waiting for REST API")
        await tak_init.wait_for_rest_api()
        # FIXME: Figure out a good way to determine if Ignite is up before calling
        #        it should be safe to assume if REST responds Ignite is up too.
        LOGGER.info("TAKIgniteOps.singleton() from locked tak_init")
        ignite_jni.TAKIgniteOps.singleton()
        LOGGER.info("tak_init.setup_tak_mgmt_conn()")
        await tak_init.setup_tak_mgmt_conn()
        LOGGER.info("tak_init.setup_tak_defaults()")
        await tak_init.setup_tak_defaults()
    except filelock.Timeout:
        LOGGER.warning("Someone has already locked {}, leaving this init to them".format(lockpath))
    finally:
        lock.release()

    # Wait for the init to be completed
    while lock.is_locked:
        LOGGER.warning("tak_init has not yet completed. Waiting for {} to be relased.".format(lockpath))
        await asyncio.sleep(2)

    LOGGER.info("TAKIgniteOps.singleton() after tak_init")
    ignite_jni.TAKIgniteOps.singleton()

    await tak_init.get_tak_defaults()

    _ = app
    # App runs
    yield
    # Cleanup
    LOGGER.info("TAKIgniteOps teardown")
    ignite_jni.TAKIgniteOps.singleton_teardown()


def get_app_no_init() -> FastAPI:
    """App init with lifespan"""
    app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=app_lifespan, version=__version__)
    app.include_router(router=all_routers, prefix="/api/v1")
    app.include_router(router=all_routers_v2, prefix="/api/v2")
    app.include_router(router=all_routers_ephemeral_v1, prefix="/ephemeral/api/v1")
    return app


def get_app() -> FastAPI:
    """Returns the FastAPI application."""
    add_trace_and_audit()
    init_logging(LOG_LEVEL)
    # Set logger levels on modules imported before logging init
    tak_init.LOGGER.setLevel(LOG_LEVEL)
    ignite_jni.LOGGER.setLevel(LOG_LEVEL)
    app = get_app_no_init()
    LOGGER.info("API init done, setting log verbosity to '{}'.".format(logging.getLevelName(LOG_LEVEL)))
    return app
