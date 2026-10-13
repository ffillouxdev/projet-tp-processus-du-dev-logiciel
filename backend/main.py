from typing import Annotated

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
async def root():
    return "Hello World"


def check_dependencies() -> dict[str, bool]:
    """Retourne la disponibilité des dépendances critiques (nom -> disponible)."""
    return {}


@app.get("/health")
def health(
    dependencies: Annotated[dict[str, bool], Depends(check_dependencies)],
) -> JSONResponse:
    """Indique l'état de santé de l'API et de ses dépendances critiques."""
    all_available = all(dependencies.values())
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
