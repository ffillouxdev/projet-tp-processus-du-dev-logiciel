from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db
from app.routers import auth_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Initialize database tables on startup
    init_db()
    yield


app = FastAPI(
    title="Tournament Platform API",
    description="API backend pour la plateforme d'organisation de tournois et d'authentification",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication router
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])


@app.get("/")
async def root() -> str:
    return "Hello World"


def check_dependencies(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, bool]:
    """Retourne la disponibilité des dépendances critiques (nom -> disponible)."""
    try:
        db.execute(text("SELECT 1"))
        return {"database": True}
    except Exception:
        return {"database": False}


@app.get("/health")
def health(
    dependencies: Annotated[dict[str, bool], Depends(check_dependencies)],
) -> JSONResponse:
    """Indique l'état de santé de l'API et de ses dépendances critiques."""
    all_available = all(dependencies.values()) if dependencies else True
    payload = {
        "status": "ok" if all_available else "unhealthy",
        "dependencies": {
            name: "ok" if available else "unavailable" for name, available in dependencies.items()
        },
    }
    return JSONResponse(
        payload,
        status_code=status.HTTP_200_OK if all_available else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
