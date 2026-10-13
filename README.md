# project-tp-process-of-the-dev-software

Subject: Tournament organization platform.

## Structure

- `backend/` — API REST FastAPI (Python 3.14, dépendances gérées par uv)
  - `main.py` — point d'entrée de l'application (`app = FastAPI()`)
  - `tests/` — tests pytest
  - `pyproject.toml` / `uv.lock` — dépendances et configuration (ruff, mypy, pytest)
- `frontend/` — interface Vue.js (à venir)

## Backend — démarrage

```sh
cd backend
uv sync
uv run fastapi dev main.py
```

## Qualité et intégration continue

La CI GitHub Actions est **bloquante** : une erreur de lint, de type ou de test fait échouer la pull request.

Backend — à exécuter depuis `backend/` :

```sh
uv sync                       # installer les dépendances
uv run ruff check .           # lint
uv run ruff format --check .  # vérification du format
uv run mypy .                 # vérification des types
uv run pytest                 # tests
```

Frontend — à exécuter depuis `frontend/` :

```sh
bun install         # installer les dépendances
bun run lint        # lint (oxlint + ESLint)
bun run type-check  # vérification des types (vue-tsc)
bun run test        # tests (vitest)
```

Les workflows `.github/workflows/backend-ci.yaml` et `.github/workflows/frontend-ci.yml` se déclenchent sur les pull requests vers `main` et `dev`. Leur statut est visible dans la pull request (onglet « Checks »).
