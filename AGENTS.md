# AGENTS.md

## Project
Monorepo « Tournament organization platform ».

- `backend/` — API FastAPI (Python 3.14, dépendances gérées avec uv)
- `frontend/` — interface Vue.js (à venir)

## Commit convention
Ce projet suit strictement [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

Format :

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

### Allowed types
| Type       | Usage                                       |
|------------|---------------------------------------------|
| `feat`     | nouvelle fonctionnalité (MINOR)             |
| `fix`      | correction de bug (PATCH)                   |
| `docs`     | documentation                               |
| `style`    | formatage, sans changement de logique       |
| `refactor` | refonte sans feature ni correction          |
| `perf`     | amélioration de performance                 |
| `test`     | ajout ou modification de tests              |
| `build`    | système de build ou dépendances             |
| `ci`       | configuration de l'intégration continue      |
| `chore`    | tâches diverses (maintien, configuration)   |
| `revert`   | annulation d'un commit                      |

### Project scopes
`backend`, `frontend`, `project`, `ci`, `docs`

### Rules
- description à l'impératif, présent, minuscule, sans point final
- scope = nom en minuscules entre parenthèses
- breaking change via `!` après le type/scope **ou** footer `BREAKING CHANGE:`
- `BREAKING CHANGE` doit être en MAJUSCULES
- corps et footers séparés par une ligne vide

### Examples
```
feat(backend): add tournament creation endpoint
fix(backend): return 404 when tournament is missing
docs(project): document backend folder
chore(backend): add ruff and pytest tooling
feat(backend)!: change tournament response schema

BREAKING CHANGE: `start_date` is now an ISO-8601 string
```

## Backend commands
À exécuter depuis `backend/` :

- `uv sync` — installer les dépendances
- `uv run ruff check .` — lint
- `uv run ruff format --check .` — vérification du format
- `uv run mypy .` — vérification des types
- `uv run pytest` — tests

## CI
Deux workflows GitHub Actions s'exécutent sur les pull requests vers `main`/`dev` et sont bloquants (toute erreur de lint, de type ou de test échoue) :

- `.github/workflows/backend-ci.yaml` — lint (ruff), format (ruff), types (mypy) et tests (pytest) lorsque `backend/**` change.
- `.github/workflows/frontend-ci.yml` — lint (oxlint + ESLint), types (vue-tsc) et tests (vitest).

Le statut est visible dans la pull request (onglet « Checks »). Le blocage effectif du merge nécessite la protection de branche (`Require status checks to pass`) sur `main` et `dev`.
