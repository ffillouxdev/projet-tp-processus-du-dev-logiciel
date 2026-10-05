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
