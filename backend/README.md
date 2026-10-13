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

## 🗄️ Base de données (PostgreSQL & SQLite)

L'ORM utilisé est **SQLAlchemy 2.0** avec le driver PostgreSQL moderne **`psycopg` (v3)**.

- **Développement local rapide** : Par défaut, l'application utilise SQLite (`sqlite:///./tournament.db`), sans configuration externe requise.
- **PostgreSQL** : Définissez simplement la variable d'environnement `DATABASE_URL` :
  ```env
  DATABASE_URL=postgresql+psycopg://utilisateur:motdepasse@localhost:5432/nom_bdd
  ```
- **Tests** : Les tests unitaires et d'intégration s'exécutent sur une base SQLite en mémoire (`sqlite:///:memory:`) totalement isolée.

---

## ⚙️ Configuration

Copiez `.env.example` vers `.env` et adaptez les valeurs :

```bash
cp .env.example .env
```

| Variable | Description | Défaut |
|---|---|---|
| `SECRET_KEY` | Clé secrète pour signer les jetons JWT | *Chaîne 64+ octets sécurisée* |
| `ALGORITHM` | Algorithme de signature JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de validité de l'access token | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Durée de validité du refresh token | `7` |
| `DATABASE_URL` | Chaîne de connexion à la base de données | `sqlite:///./tournament.db` |
| `CORS_ORIGINS` | Origines autorisées (frontend Vue.js) | `["http://localhost:3000","http://localhost:5173"]` |

---

## 🛠️ Commandes

À exécuter depuis `backend/` :

```bash
# Installation des dépendances
uv sync

# Lancer le serveur de développement avec Swagger UI
uv run fastapi dev main.py
# ou
uv run uvicorn main:app --reload

# Vérifications de qualité de code
uv run ruff check .
uv run ruff format --check .

# Exécuter l'ensemble des tests
uv run pytest
```

Documentation interactive accessible sur `http://localhost:8000/docs`.

