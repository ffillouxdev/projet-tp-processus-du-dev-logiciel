# project-tp-process-of-the-dev-software

Subject: Tournament organization platform.

## Structure

- `backend/` — API REST FastAPI (Python 3.14, dépendances gérées par uv)
  - `main.py` — point d'entrée de l'application (`app = FastAPI()`)
  - `tests/` — tests pytest
  - `pyproject.toml` / `uv.lock` — dépendances et configuration (ruff, pytest)
- `frontend/` — interface Vue.js (à venir)

## Backend — démarrage

```sh
cd backend
uv sync
uv run fastapi dev main.py
```

## Tests

```sh
cd backend
uv run pytest
```

## Santé de l'API

`GET /health` retourne l'état de l'API et de ses dépendances critiques, sans authentification.

- `200` — `{"status": "ok", "dependencies": {}}` : API et dépendances disponibles
- `503` — `{"status": "unhealthy", "dependencies": {"...": "unavailable"}}` : au moins une dépendance critique indisponible

Pour vérifier une dépendance critique, enrichir `check_dependencies()` dans `backend/main.py`.
