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
- **Profil Utilisateur (`GET /auth/me`, `PATCH /auth/me` & `GET /auth/me/memberships`)** : Récupération et mise à jour des informations de l'utilisateur connecté, ainsi que la liste de ses associations et rôles (nécessite l'Access Token en Bearer).
- **Changement de mot de passe (`POST /auth/change-password`)** : Vérification de l'ancien mot de passe, mise à jour du hash, et révocation de toutes les sessions actives.
- **Déconnexion (`POST /auth/logout`)** : Révocation du Refresh Token spécifié.
- **Déconnexion de tous les appareils (`POST /auth/logout-all`)** : Révocation de toutes les sessions de l'utilisateur connecté.

---

## 🏛️ Rôles, Associations & Organisateurs

Gestion des associations organisatrices, du catalogue des rôles et du rattachement des utilisateurs :

- **Catalogue des rôles (`/roles`)** :
  - `GET /roles` & `GET /roles/{role_id}` — consultation publique des rôles (`organizer`, `member`…).
  - `POST /roles`, `PATCH /roles/{role_id}`, `DELETE /roles/{role_id}` — création, modification et suppression d'un rôle (`409 Conflict` si le rôle est encore attribué à un membre), réservées aux administrateurs plateforme (`users.is_superuser = true`).
- **Associations (`/associations`)** :
  - `GET /associations` & `GET /associations/{association_id}` — consultation publique des associations et du détail de leurs membres/rôles.
  - `POST /associations` & `DELETE /associations/{association_id}` — création et suppression d'une association, réservées aux administrateurs plateforme (`is_superuser`).
  - `PATCH /associations/{association_id}` — modification d'une association par un administrateur plateforme ou un responsable de cette association (membre ayant le rôle `admin` ou `organizer`).
- **Membres & attribution des rôles (`/associations/{association_id}/members`)** :
  - `GET /associations/{association_id}/members` — liste publique des membres, filtrable par rôle via `?role=organizer` pour identifier qui organise.
  - `POST /associations/{association_id}/members` — associer un utilisateur (`user_id`) à l'association avec un rôle (`role_id`).
  - `PATCH /associations/{association_id}/members/{user_id}` — modifier le rôle d'un membre dans l'association.
  - `DELETE /associations/{association_id}/members/{user_id}` — retirer un utilisateur de l'association.
  - Les opérations d'écriture sur les membres sont autorisées aux administrateurs plateforme (`is_superuser`) ainsi qu'aux membres actifs détenant le rôle `admin` ou `organizer` au sein de l'association ciblée (`401` si non authentifié, `403` sinon).

---

## 🏆 Tournois & Contrôle d'Accès (`/tournaments`)

Gestion des tournois et filtrage serveur selon les droits de l'utilisateur :

- **Consultation & visibilité (`GET /tournaments`, `GET /associations/{association_id}/tournaments`, `GET /tournaments/{tournament_id}`)** :
  - **Tournois publiés (`open`, `ongoing`, `finished`)** : visibles par tous (authentifiés ou non).
  - **Tournois protégés (`draft`)** : visibles uniquement par les membres de l'association organisatrice (rôle `member`, `organizer`, `admin`…) et les administrateurs plateforme (`users.is_superuser = true`).
  - Les filtres d'accès sont appliqués côté serveur aussi bien sur la liste (y compris avec les filtres `?association_id=...` et `?status=...`) que lors d'un accès direct par identifiant (`403 Forbidden` si l'utilisateur n'a pas les droits sur un tournoi protégé, `404 Not Found` si le tournoi n'existe pas).
- **Administration des tournois (`POST /tournaments`, `PATCH /tournaments/{tournament_id}`, `DELETE /tournaments/{tournament_id}`)** :
  - Création, modification (ex. publication d'un brouillon `draft` vers `open`) et suppression réservées aux administrateurs plateforme (`is_superuser`) et aux responsables (`organizer` / `admin`) de l'association organisatrice (`401` si non authentifié, `403` sinon).
- **Lancement du tournoi & Arbre à élimination directe (`/tournaments/{tournament_id}/start` & `/bracket`)** :
  - `POST /tournaments/{tournament_id}/start` : lance le tournoi (au moins 2 participants requis), génère aléatoirement l'arbre à élimination directe (exempts/BYEs répartis pour qu'aucun match du 1er tour n'oppose deux BYEs) et passe le statut à `ongoing`.
  - `GET /tournaments/{tournament_id}/bracket` : retourne l'arbre du tournoi formaté pour le composant frontend `SingleEliminationBracket`.
- **Renseignement du score d'un match (`PATCH /tournaments/{tournament_id}/matches/{match_id}/score`)** :
  - Saisie du score (`score_player1`, `score_player2` entiers $\ge 0$ et sans égalité).
  - Autorisé pour les **joueurs du match**, les responsables de l'association (`organizer`/`admin`) et les superusers.
  - Avancement automatique du vainqueur vers le tour suivant (`next_match_id`).
  - Saisie possible uniquement tant que le tournoi est `ongoing` (`409 Conflict` sinon) : les résultats d'un tournoi clôturé sont figés.
- **Clôture de l'événement** :
  - La validation du score de la finale passe automatiquement le tournoi au statut `finished` et enregistre son vainqueur (`tournaments.winner_id`).
  - Le vainqueur est exposé par `GET /tournaments` et `GET /associations/{association_id}/tournaments` (`winner_id`), par `GET /tournaments/{tournament_id}` (`winner` : `id`, `username`, `full_name`) et par la réponse de saisie du score (`tournament_winner_id`).
  - Repasser un tournoi `finished` à un autre statut via `PATCH /tournaments/{tournament_id}` efface son vainqueur.
- **Inscription à un tournoi (`POST /tournaments/{tournament_id}/participants`)** :
  - Le lien public d'un tournoi est son URL `/tournaments/{tournament_id}` ; tout utilisateur authentifié et actif peut s'y inscrire (`201 Created`, renvoie l'inscription).
  - Refus : `401` si non authentifié, `403` si compte inactif ou brouillon non visible, `404` si le tournoi n'existe pas, `409 Conflict` si les inscriptions ne sont pas ouvertes (statut différent de `open`), si l'utilisateur est déjà inscrit ou si `max_participants` est atteint.
- **Désinscription (`DELETE /tournaments/{tournament_id}/participants/me`)** :
  - L'utilisateur authentifié annule sa propre inscription tant que le tournoi est `open` (`204 No Content`).
  - Refus : `401` si non authentifié, `403` si compte inactif ou brouillon non visible, `404` si le tournoi n'existe pas ou si l'utilisateur n'y est pas inscrit, `409 Conflict` si les inscriptions ne sont plus ouvertes (tournoi lancé ou terminé).

---

## 🗄️ Base de données (PostgreSQL + Alembic)

L'ORM utilisé est **SQLAlchemy 2** avec le driver **`psycopg` (v3)**. **PostgreSQL 17 est le seul moteur**, en développement, en test et en CI (SQLite n'est plus utilisé).
Le schéma est défini **uniquement par les migrations versionnées [Alembic](https://alembic.sqlalchemy.org/)** situées dans `migrations/versions/` :

| Révision | Contenu |
|---|---|
| `0001_initial_schema` | `users`, `refresh_tokens` |
| `0002_associations_roles_tournaments` | `associations`, `roles`, `memberships` (utilisateur ↔ association avec un rôle), `tournaments`, `tournament_participants` (utilisateur ↔ tournoi) |
| `0003_add_matches_table` | `matches` (arbre de tournoi à élimination directe, rounds et vainqueurs) |
| `0004_add_tournament_winner` | colonne `tournaments.winner_id` (vainqueur du tournoi, renseigné à la validation de la finale) |

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

### Données de démonstration

```bash
make db-seed    # applique les migrations puis charge le jeu de démo
```

Sans `make` : `uv run python -m app.seed`. Le chargement est **idempotent** : chaque enregistrement est retrouvé par sa clé naturelle (nom d'utilisateur, nom de rôle, nom d'association, nom du tournoi dans son association) puis mis à jour. Relancer la commande ne crée donc aucun doublon et remet les comptes de démo dans leur état initial. Pour repartir de zéro : `make db-reset && make db-seed`.

> ⚠️ **Réservé à l'environnement de démo.** Tous les comptes partagent le mot de passe public **`Demo1234!`**. La commande refuse de s'exécuter si `ENVIRONMENT=production`.

| Utilisateur | E-mail | Profil |
|---|---|---|
| `admin` | `admin@demo.example.com` | administrateur plateforme (`is_superuser`) |
| `alice` | `alice@demo.example.com` | organizer de **Avignon Chess Club** |
| `bob` | `bob@demo.example.com` | organizer de **Vaucluse eSport** |
| `chloe` | `chloe@demo.example.com` | member de Avignon Chess Club, inscrite à des tournois des deux associations |
| `david` | `david@demo.example.com` | member de Vaucluse eSport |
| `emma` | `emma@demo.example.com` | member de Vaucluse eSport |
| `hugo` | `hugo@demo.example.com` | compte **désactivé** (connexion refusée, 403) |

On peut se connecter avec le nom d'utilisateur ou l'e-mail. Le jeu contient aussi 6 tournois, 3 par association, couvrant les statuts `draft`, `open`, `ongoing` et `finished`. Les dates sont calculées par rapport au jour du chargement. Les tournois `draft` n'ont aucun inscrit et les inscriptions respectent `max_participants`. Le contenu se modifie dans `app/seed.py`.

### Gérer un administrateur plateforme en CLI

En dehors du jeu de démo, un administrateur plateforme (`is_superuser = true`) peut être créé ou promu via `app.db` :

```bash
uv run python -m app.db create-admin --email admin@example.com --username superadmin --password "Secret1234"
uv run python -m app.db promote-admin <username_ou_email>
```

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

# Démarrer PostgreSQL, appliquer les migrations et charger le jeu de démo
make db-init
make db-seed

# Lancer le serveur de développement avec Swagger UI
uv run fastapi dev main.py
# ou
uv run uvicorn main:app --reload

# Vérifications de qualité de code et de typage
uv run ruff check .
uv run ruff format --check .
uv run mypy .

# Exécuter l'ensemble des tests (Docker requis)
uv run pytest
```

Documentation interactive accessible sur `http://localhost:8000/docs`.

