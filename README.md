# project-tp-process-of-the-dev-software

Subject: Tournament organization platform.

## Structure

- `backend/` — API REST FastAPI (Python 3.14, dépendances gérées par uv)
  - `main.py` — point d'entrée de l'application (`app = FastAPI()`)
  - `app/models/` — modèles SQLAlchemy (users, associations, roles, memberships, tournaments, participants…)
  - `migrations/` — migrations Alembic versionnées (seule source du schéma)
  - `tests/` — tests pytest (PostgreSQL via testcontainers)
  - `pyproject.toml` / `uv.lock` — dépendances et configuration (ruff, mypy, pytest)
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
uv run python -m app.seed                 # charger les données de démo (= make db-seed, idempotent)
docker compose down                       # arrêter (ajouter -v pour supprimer le volume)
```

Détails (variables, création d'une migration, comptes de démo) : [`backend/README.md`](backend/README.md#️-base-de-données-postgresql--alembic).

> Les comptes de démo (`admin`, `alice`, `bob`…, mot de passe `Demo1234!`) sont **réservés à l'environnement de démo** : voir [Données de démonstration](backend/README.md#données-de-démonstration).

## Backend — démarrage

```sh
cd backend
uv sync
cp .env.example .env
make db-init                # PostgreSQL + migrations
uv run fastapi dev main.py  # applique aussi les migrations en attente au démarrage
```

## Qualité et intégration continue

La CI GitHub Actions est **bloquante** : une erreur de lint, de type ou de test fait échouer la pull request.

Backend — à exécuter depuis `backend/` :

Docker doit être démarré : les tests lancent un PostgreSQL éphémère (testcontainers).

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

La CI (`.github/workflows/backend-ci.yaml`) exécute lint, tests et un job `migrations`
(`alembic upgrade head`, `alembic check`, `alembic downgrade base`).

Les workflows `.github/workflows/backend-ci.yaml` et `.github/workflows/frontend-ci.yml` se déclenchent sur les pull requests vers `main` et `dev`. Leur statut est visible dans la pull request (onglet « Checks »).

## Santé de l'API

`GET /health` retourne l'état de l'API et de ses dépendances critiques, sans authentification.

- `200` — `{"status": "ok", "dependencies": {}}` : API et dépendances disponibles
- `503` — `{"status": "unhealthy", "dependencies": {"...": "unavailable"}}` : au moins une dépendance critique indisponible

Pour vérifier une dépendance critique, enrichir `check_dependencies()` dans `backend/main.py`.
