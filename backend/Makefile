COMPOSE := docker compose -f ../compose.yaml

.PHONY: db-up db-down db-init db-reset

db-up: ## Start PostgreSQL and wait until it is healthy
	$(COMPOSE) up -d --wait db

db-down: ## Stop PostgreSQL (data is kept in the pgdata volume)
	$(COMPOSE) down

db-init: db-up ## Create or upgrade the schema to the latest migration
	uv run python -m app.db init

db-reset: db-up ## Drop every table and re-apply all migrations (data loss)
	uv run python -m app.db reset
