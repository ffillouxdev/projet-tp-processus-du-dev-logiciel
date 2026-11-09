from app.routers.associations import router as associations_router
from app.routers.auth import router as auth_router
from app.routers.roles import router as roles_router
from app.routers.tournaments import router as tournaments_router

__all__ = ["associations_router", "auth_router", "roles_router", "tournaments_router"]
