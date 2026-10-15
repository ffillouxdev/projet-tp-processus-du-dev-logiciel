# Tournament Platform - Backend API

API FastAPI pour la plateforme d'organisation de tournois et la gestion d'authentification.

## 🚀 Fonctionnalités d'Authentification

L'API implémente un système d'authentification complet et sécurisé respectant les standards de l'industrie (OWASP, RFC 7519, OAuth2) :

- **Inscription (`POST /auth/register`)** : Création de compte avec validation d'email, unicité (409 Conflict), mot de passe sécurisé (min. 8 caractères, lettres et chiffres requis). Le mot de passe est haché avec **Argon2id**. Retourne les informations utilisateur et les jetons d'accès.
- **Connexion (`POST /auth/login`)** : Authentification via email ou nom d'utilisateur et mot de passe.
- **Endpoint OAuth2 (`POST /auth/token`)** : Endpoint compatible avec le standard `OAuth2PasswordRequestForm` (permettant le bouton "Authorize" de Swagger UI `/docs`).
- **Persistance de session et rafraîchissement (`POST /auth/refresh`)** :
  - **Access Token** : JWT de courte durée (15 minutes par défaut) pour sécuriser les requêtes.
  - **Refresh Token** : JWT de longue durée (7 jours par défaut) stocké en base de données avec identifiant unique (`jti`).
  - **Rotation de jetons** : À chaque rafraîchissement, l'ancien refresh token est révoqué et une nouvelle paire est émise.
  - **Détection d'attaque par rejeu (Replay Attack Detection)** : La réutilisation d'un refresh token déjà révoqué invalide immédiatement toutes les sessions actives de l'utilisateur.
- **Profil Utilisateur (`GET /auth/me` & `PATCH /auth/me`)** : Récupération et mise à jour des informations de l'utilisateur connecté (nécessite l'Access Token en Bearer).
- **Changement de mot de passe (`POST /auth/change-password`)** : Vérification de l'ancien mot de passe, mise à jour du hash, et révocation de toutes les sessions actives.
- **Déconnexion (`POST /auth/logout`)** : Révocation du Refresh Token spécifié.
- **Déconnexion de tous les appareils (`POST /auth/logout-all`)** : Révocation de toutes les sessions de l'utilisateur connecté.

---

## 🗄️ Base de données (PostgreSQL + Alembic)

L'ORM utilisé est **SQLAlchemy 2** avec le driver **`psycopg` (v3)**. **PostgreSQL 17 est le seul moteur**, en développement, en test et en CI (SQLite n'est plus utilisé).
Le schéma est défini **uniquement par les migrations versionnées [Alembic](https://alembic.sqlalchemy.org/)** situées dans `migrations/versions/` :

| Révision | Contenu |
|---|---|
| `0001_initial_schema` | `users`, `refresh_tokens` |
| `0002_associations_roles_tournaments` | `associations`, `roles`, `memberships` (utilisateur ↔ association avec un rôle), `tournaments`, `tournament_participants` (utilisateur ↔ tournoi) |

![MCD du schéma](../docs/mcd.svg)

> Règle de gestion : tout utilisateur est **participant** par défaut, même sans association (statut implicite, non stocké). Les rôles de `memberships` (organizer…) s'y ajoutent au sein d'une association, et chaque rôle est attribué au moins une fois (cardinalité 1,n, non contrainte en base) ; l'administrateur plateforme est `users.is_superuser`.

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) avec Docker Compose (base locale **et** tests)
- [uv](https://docs.astral.sh/uv/)

### Démarrer la base

Le service `db` (`postgres:17-alpine`) est défini dans `compose.yaml` à la racine du dépôt. Les identifiants sont lus depuis le `.env` racine (valeurs par défaut : `postgres` / `postgres` / `tournament_db`, port `5432`) :

```bash
cp ../.env.example ../.env   # optionnel : adapter les identifiants
cp .env.example .env         # DATABASE_URL doit correspondre aux identifiants ci-dessus
make db-up                   # docker compose -f ../compose.yaml up -d --wait db
```

### Créer / réinitialiser la base

```bash
make db-init    # applique toutes les migrations (crée le schéma sur une base vide)
make db-reset   # ⚠️ supprime toutes les tables et données puis réapplique les migrations
make db-down    # arrête PostgreSQL (les données restent dans le volume pgdata)
```

Sans `make` : `uv run python -m app.db init|reset`, ou directement `uv run alembic upgrade head` / `uv run alembic downgrade base`.

Au démarrage de l'API (`fastapi dev`), les migrations en attente sont **appliquées automatiquement** (`alembic upgrade head`), sauf si `ENVIRONMENT=test`.

Pour repartir d'un volume totalement vierge : `docker compose -f ../compose.yaml down -v && make db-init`.

### Créer une nouvelle migration

1. Modifier/ajouter le modèle dans `app/models/` (et l'exporter dans `app/models/__init__.py`).
2. Base à jour : `make db-init`.
3. Générer la révision :
   ```bash
   uv run alembic revision --autogenerate --rev-id 0003 -m "add matches table"
   ```
   Le fichier `migrations/versions/0003_add_matches_table.py` est formaté automatiquement par ruff.
4. **Relire la révision** : l'autogenerate ne détecte pas tout (renommages, contraintes `CHECK`, données). Vérifier que `downgrade()` annule exactement `upgrade()`.
5. Tester l'aller-retour puis l'absence d'écart modèles ↔ migrations :
   ```bash
   uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
   uv run alembic check
   ```
6. Commiter le modèle **et** la révision ensemble. Ne jamais modifier une révision déjà mergée : en créer une nouvelle.

Autres commandes utiles : `uv run alembic current`, `uv run alembic history`, `uv run alembic upgrade head --sql` (SQL sans exécution).

### Tests

Les tests s'exécutent sur un **vrai PostgreSQL** : un conteneur éphémère `postgres:17-alpine` est démarré pour la session par [testcontainers](https://testcontainers-python.readthedocs.io/) (**Docker requis**), et son schéma est créé par `alembic upgrade head` — les migrations sont donc testées à chaque exécution. Chaque test tourne dans une transaction annulée à la fin (isolation complète).

Pour utiliser une base existante plutôt qu'un conteneur, définir `TEST_DATABASE_URL` (base **dédiée** aux tests) :

```bash
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/tournament_test uv run pytest
```

---

## 🛠️ Commandes

À exécuter depuis `backend/` :

```bash
# Installation des dépendances
uv sync

# Démarrer PostgreSQL et appliquer les migrations
make db-init

# Lancer le serveur de développement avec Swagger UI
uv run fastapi dev main.py
# ou
uv run uvicorn main:app --reload

# Vérifications de qualité de code
uv run ruff check .
uv run ruff format --check .

# Exécuter l'ensemble des tests (Docker requis)
uv run pytest
```

Documentation interactive accessible sur `http://localhost:8000/docs`.

