# project-tp-process-of-the-dev-software

Subject: Tournament organization platform.

## Structure

- `backend/` — API REST FastAPI (Python 3.14, dépendances gérées par uv)
  - `main.py` — point d'entrée de l'application (`app = FastAPI()`)
  - `app/models/` — modèles SQLAlchemy (users, roles, associations, tournaments…)
  - `migrations/` — migrations Alembic versionnées (seule source du schéma)
  - `tests/` — tests pytest (PostgreSQL via testcontainers)
  - `pyproject.toml` / `uv.lock` — dépendances et configuration (ruff, pytest)
- `compose.yaml` — service PostgreSQL 17 (`db`) pour le développement
- `docs/` — documentation (MCD de la base : `docs/mcd.svg`)
- `frontend/` — interface Vue.js (à venir)

## Base de données

PostgreSQL 17 (seul moteur, via Docker) ; schéma géré par les migrations Alembic.
Modèle conceptuel des données : [`docs/mcd.svg`](docs/mcd.svg).

```sh
cp .env.example .env                      # identifiants PostgreSQL (optionnel)
docker compose up -d --wait db            # démarrer PostgreSQL
cd backend
uv run alembic upgrade head               # créer / mettre à jour le schéma (= make db-init)
uv run python -m app.db reset             # réinitialiser la base (= make db-reset, perte des données)
docker compose down                       # arrêter (ajouter -v pour supprimer le volume)
```

Détails (variables, création d'une migration) : [`backend/README.md`](backend/README.md#️-base-de-données-postgresql--alembic).

## Backend — démarrage

```sh
cd backend
uv sync
cp .env.example .env
make db-init                # PostgreSQL + migrations
uv run fastapi dev main.py  # applique aussi les migrations en attente au démarrage
```

## Tests

Docker doit être démarré : les tests lancent un PostgreSQL éphémère (testcontainers).

```sh
cd backend
uv run pytest
```

La CI (`.github/workflows/backend-ci.yaml`) exécute lint, tests et un job `migrations`
(`alembic upgrade head`, `alembic check`, `alembic downgrade base`).

## Santé de l'API

`GET /health` retourne l'état de l'API et de ses dépendances critiques, sans authentification.

- `200` — `{"status": "ok", "dependencies": {}}` : API et dépendances disponibles
- `503` — `{"status": "unhealthy", "dependencies": {"...": "unavailable"}}` : au moins une dépendance critique indisponible

Pour vérifier une dépendance critique, enrichir `check_dependencies()` dans `backend/main.py`.
