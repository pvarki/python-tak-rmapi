"""Api endpoints"""

from fastapi.routing import APIRouter

from .usercrud import router as usercrud_router
from .clientinfo import router as clientinfo_router
from .admininfo import router as admininfo_router
from .healthcheck import router as healthcheck_router
from .description import router as description_router
from .instructions import router as instructions_router
from .tak_datapackage import router as takdatapackage_router

all_routers = APIRouter()
all_routers.include_router(usercrud_router, prefix="/users", tags=["users"])
all_routers.include_router(clientinfo_router, prefix="/clients", tags=["clients"])
all_routers.include_router(admininfo_router, prefix="/admins", tags=["admins"])
all_routers.include_router(healthcheck_router, prefix="/healthcheck", tags=["healthcheck"])
all_routers.include_router(description_router, prefix="/description", tags=["description"])
all_routers.include_router(instructions_router, prefix="/instructions", tags=["instructions"])
all_routers.include_router(takdatapackage_router, prefix="/tak-datapackages", tags=["tak-datapackages"])
