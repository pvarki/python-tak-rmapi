"""Api endpoints"""
from fastapi.routing import APIRouter

from .usercrud import router as usercrud_router
from .usercrud import test_router as testing_router  # REMOVE ME
from .clientinfo import router as clientinfo_router
from .admininfo import router as admininfo_router
from .healthcheck import router as healthcheck_router

all_routers = APIRouter()
all_routers.include_router(testing_router, prefix="/users", tags=["users"])  # REMOVE ME
all_routers.include_router(usercrud_router, prefix="/users", tags=["users"])
all_routers.include_router(clientinfo_router, prefix="/clients", tags=["clients"])
all_routers.include_router(admininfo_router, prefix="/admins", tags=["admins"])
all_routers.include_router(healthcheck_router, prefix="/healthcheck", tags=["healthcheck"])
