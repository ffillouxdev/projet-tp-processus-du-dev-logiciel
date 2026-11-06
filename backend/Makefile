DOCKER_COMPOSE_V2 := $(shell docker compose version >/dev/null 2>&1 && echo 1)
ifeq ($(DOCKER_COMPOSE_V2),1)
COMPOSE := docker compose -f ../compose.yaml
COMPOSE_UP := $(COMPOSE) up -d --wait db
else
COMPOSE := docker-compose -f ../compose.yaml
COMPOSE_UP := $(COMPOSE) up -d db && until $(COMPOSE) exec -T db pg_isready -q; do sleep 1; done
endif

UV := $(shell command -v uv 2>/dev/null || echo ./.bin/uv)

.PHONY: db-up db-down db-init db-reset db-seed

db-up: ## Start PostgreSQL and wait until it is healthy
	$(COMPOSE_UP)

db-down: ## Stop PostgreSQL (data is kept in the pgdata volume)
	$(COMPOSE) down

db-init: db-up ## Create or upgrade the schema to the latest migration
	$(UV) run python -m app.db init

db-reset: db-up ## Drop every table and re-apply all migrations (data loss)
	$(UV) run python -m app.db reset

db-seed: db-init ## Load the demo dataset (idempotent, demo environment only)
	$(UV) run python -m app.seed
