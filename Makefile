.DEFAULT_GOAL := help

-include .env
MOSAIC_HOST ?= 127.0.0.1
MOSAIC_PORT ?= 8000
.PHONY: help setup dev dev-api dev-web test lint format typecheck openapi client contracts-check build clean

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

setup: ## Install Python and web dependencies and git hooks
	uv sync
	cd web && pnpm install
	uv run pre-commit install

dev: ## Run API (MOSAIC_PORT, default 8000) and web (:5173) together
	@trap 'trap - INT TERM EXIT; kill 0' INT TERM EXIT; $(MAKE) dev-api & $(MAKE) dev-web & wait

dev-api:
	uv run uvicorn mosaic_api.main:app --host $(MOSAIC_HOST) --port $(MOSAIC_PORT) --reload --reload-dir packages

dev-web:
	cd web && VITE_API_TARGET=http://$(MOSAIC_HOST):$(MOSAIC_PORT) pnpm dev

test: ## Run all tests
	uv run pytest
	cd web && pnpm test

lint: ## Lint and format-check everything
	uv run ruff check .
	uv run ruff format --check .
	cd web && pnpm lint && pnpm format:check

format: ## Auto-format everything
	uv run ruff check --fix .
	uv run ruff format .
	cd web && pnpm format

typecheck: ## Type-check Python and TypeScript
	uv run mypy packages scripts
	cd web && pnpm typecheck

openapi: ## Export OpenAPI schema to contracts/
	uv run python scripts/export_openapi.py

client: openapi ## Regenerate the TypeScript API types from contracts/
	cd web && pnpm client

contracts-check: client ## Fail if contracts/ or the generated client are stale
	git diff --exit-code -- contracts web/src/api/generated

build: ## Production build of the web app
	cd web && pnpm build

clean: ## Remove build output and caches (keeps data/)
	rm -rf web/dist .pytest_cache .mypy_cache .ruff_cache
