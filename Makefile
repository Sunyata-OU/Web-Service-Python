# Web Service Template - Makefile
# Provides convenient commands for development, deployment, and operations

# Colors for help output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
RESET := \033[0m

# Default environment
ENV ?= local
COMPOSE_FILE := docker-compose.yml
ifeq ($(ENV),debug)
	COMPOSE_FILE := docker-compose-debug.yml
endif

# Help target (default)
.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)Web Service Template - Available Commands$(RESET)"
	@echo ""
	@echo "$(YELLOW)Development:$(RESET)"
	@awk '/^[a-zA-Z\-_0-9]+:.*?## .*Development.*/ { printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, substr($$0, index($$0, $$3)) }' $(MAKEFILE_LIST) | grep "Development"
	@echo ""
	@echo "$(YELLOW)Testing & Quality:$(RESET)"
	@awk '/^[a-zA-Z\-_0-9]+:.*?## .*Test.*|.*Quality.*|.*Lint.*|.*Format.*/ { printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, substr($$0, index($$0, $$3)) }' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Deployment:$(RESET)"
	@awk '/^[a-zA-Z\-_0-9]+:.*?## .*Deploy.*|.*SSL.*|.*Production.*/ { printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, substr($$0, index($$0, $$3)) }' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Operations:$(RESET)"
	@awk '/^[a-zA-Z\-_0-9]+:.*?## .*Operation.*|.*Backup.*|.*Monitor.*|.*Log.*/ { printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, substr($$0, index($$0, $$3)) }' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Database:$(RESET)"
	@awk '/^[a-zA-Z\-_0-9]+:.*?## .*Database.*|.*Migration.*/ { printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, substr($$0, index($$0, $$3)) }' $(MAKEFILE_LIST)
	@echo ""

# Development Commands
.PHONY: init
init: ## Development - Complete project initialization
	@echo "$(BLUE)Initializing Web Service Template...$(RESET)"
	@make sync-new-env
	@make install
	pre-commit install
	docker compose build
	$(MAKE) migrate
	docker compose up -d db redis_db minio
	sleep 10
	$(MAKE) create-bucket
	@echo "$(GREEN)✅ Initialization complete!$(RESET)"
	@echo "$(YELLOW)Next steps:$(RESET)"
	@echo "  1. Edit .env file with your configuration"
	@echo "  2. Run: make dev"

sync-new-env:
	@if [ ! -f .env ]; then cp .env-copy .env && echo "$(GREEN)Created .env file from template$(RESET)"; fi
	@while IFS='=' read -r key value; do \
		if [ -n "$$key" ] && [ "$${key#\#}" = "$$key" ]; then \
			if ! grep -q "^$$key=" .env; then \
				echo "$$key=$$value" >> .env; \
				echo "$(YELLOW)Added missing variable: $$key$(RESET)"; \
			fi; \
		fi; \
	done < .env-copy

.PHONY: dev
dev: ## Development - Start development environment
	@echo "$(BLUE)Starting development environment...$(RESET)"
	docker compose -f $(COMPOSE_FILE) up --build

.PHONY: dev-bg
dev-bg: ## Development - Start development environment in background
	@echo "$(BLUE)Starting development environment in background...$(RESET)"
	docker compose -f $(COMPOSE_FILE) up --build -d

.PHONY: install
install: ## Development - Install Python dependencies with uv
	@echo "$(BLUE)Installing dependencies with uv...$(RESET)"
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "$(YELLOW)Installing uv...$(RESET)"; \
		pip install uv; \
	fi
	uv sync --dev

.PHONY: shell
shell: ## Development - Activate uv virtual environment
	@echo "$(BLUE)Activating virtual environment...$(RESET)"
	@echo "Run: source .venv/bin/activate"

debugger: ## Development - Start with debugger support
	@echo "$(BLUE)Starting development with debugger support...$(RESET)"
	@docker compose -f docker-compose-debug.yml up

# Testing & Quality Commands
.PHONY: test
test: ## Test - Run all tests
	@echo "$(BLUE)Running tests...$(RESET)"
	uv run pytest

.PHONY: lint
lint: ## Quality - Run code linting
	@echo "$(BLUE)Running linting checks...$(RESET)"
	uv run ruff check .

.PHONY: format
format: ## Quality - Format code
	@echo "$(BLUE)Formatting code...$(RESET)"
	uv run ruff format .

.PHONY: type-check
type-check: ## Quality - Run type checking
	@echo "$(BLUE)Running type checks...$(RESET)"
	uv run mypy src/

.PHONY: quality
quality: lint format type-check test ## Quality - Run all quality checks

.PHONY: pre-commit
pre-commit: ## Quality - Run pre-commit hooks on all files
	uv run pre-commit run --all-files

.PHONY: add
add: ## Development - Add a new dependency (usage: make add PACKAGE=package-name)
	@if [ -z "$(PACKAGE)" ]; then echo "$(RED)Error: PACKAGE required. Usage: make add PACKAGE=package-name$(RESET)"; exit 1; fi
	uv add $(PACKAGE)

.PHONY: add-dev
add-dev: ## Development - Add a development dependency (usage: make add-dev PACKAGE=package-name)
	@if [ -z "$(PACKAGE)" ]; then echo "$(RED)Error: PACKAGE required. Usage: make add-dev PACKAGE=package-name$(RESET)"; exit 1; fi
	uv add --dev $(PACKAGE)

# Deployment Commands
.PHONY: build
build: ## Deploy - Build Docker images
	@echo "$(BLUE)Building Docker images...$(RESET)"
	docker compose build

.PHONY: build-ssh
build-ssh: ## Deploy - Build Docker images with SSH agent forwarding
	@echo "$(BLUE)Building Docker images with SSH support...$(RESET)"
	docker compose build --ssh default

.PHONY: deploy-prod
deploy-prod: ## Deploy - Deploy to production with SSL
	@echo "$(BLUE)Deploying to production...$(RESET)"
	@echo "$(YELLOW)⚠️  Make sure SSL certificates are set up first!$(RESET)"
	docker compose --profile nginx up --build -d
	$(MAKE) health-check

.PHONY: deploy-local
deploy-local: ## Deploy - Deploy locally without SSL
	@echo "$(BLUE)Deploying locally...$(RESET)"
	docker compose up --build -d

.PHONY: ssl-init
ssl-init: ## SSL - Initialize SSL certificates (requires EMAIL)
	@if [ -z "$(EMAIL)" ]; then echo "$(RED)Error: EMAIL required. Usage: make ssl-init EMAIL=your@email.com$(RESET)"; exit 1; fi
	./scripts/init-ssl.sh --email $(EMAIL) --verbose

.PHONY: ssl-renew
ssl-renew: ## SSL - Force SSL certificate renewal
	@if [ -z "$(EMAIL)" ]; then echo "$(RED)Error: EMAIL required. Usage: make ssl-renew EMAIL=your@email.com$(RESET)"; exit 1; fi
	./scripts/init-ssl.sh --email $(EMAIL) --force --verbose

# Operations Commands
.PHONY: status
status: ## Operation - Show service status
	docker compose ps

.PHONY: logs
logs: ## Operation - Show logs for all services
	docker compose logs -f

.PHONY: logs-app
logs-app: ## Operation - Show FastAPI application logs
	docker compose logs -f fastapi

.PHONY: logs-nginx
logs-nginx: ## Operation - Show Nginx logs
	docker compose logs -f nginx

.PHONY: health-check
health-check: ## Operation - Run health checks
	@echo "$(BLUE)Running health checks...$(RESET)"
	@if [ -f scripts/monitor.sh ]; then ./scripts/monitor.sh $(ENV); else echo "$(YELLOW)Health check script not available$(RESET)"; fi

.PHONY: backup
backup: ## Operation - Create system backup
	@echo "$(BLUE)Creating backup...$(RESET)"
	@if [ -f scripts/backup.sh ]; then ./scripts/backup.sh; else echo "$(YELLOW)Backup script not available yet$(RESET)"; fi

.PHONY: monitor
monitor: ## Operation - Run monitoring checks
	@if [ -f scripts/monitor.sh ]; then ./scripts/monitor.sh $(ENV); else echo "$(YELLOW)Monitor script not available yet$(RESET)"; fi

.PHONY: clean
clean: ## Operation - Clean up Docker resources
	@echo "$(BLUE)Cleaning up Docker resources...$(RESET)"
	docker compose down
	docker system prune -f
	docker volume prune -f

.PHONY: clean-all
clean-all: ## Operation - Clean up everything (including data)
	@echo "$(RED)⚠️  This will delete all data! Are you sure?$(RESET)"
	@read -p "Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ]
	docker compose down -v
	docker system prune -af
	docker volume prune -af

.PHONY: restart
restart: ## Operation - Restart all services
	@echo "$(BLUE)Restarting services...$(RESET)"
	docker compose restart

.PHONY: stop
stop: ## Operation - Stop all services
	@echo "$(BLUE)Stopping services...$(RESET)"
	docker compose down

# Database Commands
alembic-autogenerate: ## Database - Create new migration interactively
	@read -p "Enter migration message: " message; \
	alembic revision --autogenerate -m "$$message"

alembic-upgrade: ## Database - Run database migrations
	alembic upgrade head

migrate: alembic-upgrade ## Database - Alias for alembic-upgrade

.PHONY: migration
migration: ## Database - Create new migration (requires MESSAGE)
	@if [ -z "$(MESSAGE)" ]; then echo "$(RED)Error: MESSAGE required. Usage: make migration MESSAGE='description'$(RESET)"; exit 1; fi
	alembic revision --autogenerate -m "$(MESSAGE)"

.PHONY: db-shell
db-shell: ## Database - Open PostgreSQL shell
	docker compose exec db psql -U postgres -d $$(grep POSTGRES_DB .env | cut -d'=' -f2)

.PHONY: redis-shell
redis-shell: ## Database - Open Redis shell
	docker compose exec redis_db redis-cli

.PHONY: create-bucket
create-bucket: ## Database - Create MinIO S3 bucket
	@echo "$(BLUE)Creating S3 bucket...$(RESET)"
	docker compose up createbuckets

# Container Management
.PHONY: exec-app
exec-app: ## Operation - Execute shell in FastAPI container
	docker compose exec fastapi bash

.PHONY: exec-db
exec-db: ## Operation - Execute shell in database container
	docker compose exec db bash

.PHONY: exec-nginx
exec-nginx: ## Operation - Execute shell in nginx container
	docker compose exec nginx sh

# Environment Setup
.PHONY: env-check
env-check: ## Development - Check environment configuration
	@echo "$(BLUE)Environment Configuration:$(RESET)"
	@echo "Current environment: $(ENV)"
	@echo "Compose file: $(COMPOSE_FILE)"
	@if [ -f .env ]; then echo "$(GREEN).env file exists$(RESET)"; else echo "$(RED).env file missing$(RESET)"; fi
	@echo "$(BLUE)Key Environment Variables:$(RESET)"
	@grep -E "^(DOMAIN|SERVICE_PORT|POSTGRES_DB)=" .env 2>/dev/null || echo "$(YELLOW)Some variables not set$(RESET)"

# Development shortcuts
.PHONY: up
up: dev-bg ## Shortcut for dev-bg

.PHONY: down
down: stop ## Shortcut for stop

.PHONY: rebuild
rebuild: ## Development - Rebuild and restart services
	docker compose up --build -d

# Production helpers
.PHONY: prod-logs
prod-logs: ## Production - Show production logs with nginx
	docker compose --profile nginx logs -f

.PHONY: prod-status
prod-status: ## Production - Show production service status
	docker compose --profile nginx ps

.PHONY: nginx-reload
nginx-reload: ## Production - Reload nginx configuration
	docker compose exec nginx nginx -s reload

# Default target
.DEFAULT_GOAL := help
