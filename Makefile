.PHONY: help build up down restart logs shell clean prune dev prod backup restore status health env-setup

# Configuration
IMAGE_NAME := last-war-scheduler
CONTAINER_NAME := last_war_scheduler
PORT := 8501

# Load environment variables if .env exists
-include .env
export

# Default target
help:
	@echo "Last War Scheduler - Docker Management"
	@echo ""
	@echo "Available targets:"
	@echo "  build       - Build the Docker image"
	@echo "  up          - Start the container in detached mode"
	@echo "  down        - Stop and remove the container"
	@echo "  restart     - Restart the container"
	@echo "  logs        - View container logs (follow mode)"
	@echo "  logs-tail   - View last 100 lines of logs"
	@echo "  shell       - Open a shell in the running container"
	@echo "  clean       - Remove container and image"
	@echo "  prune       - Clean up all Docker resources"
	@echo "  dev         - Start in development mode with hot reload"
	@echo "  prod        - Start in production mode"
	@echo "  backup      - Backup data directory"
	@echo "  restore     - Restore data directory from backup"
	@echo "  status      - Show container status"
	@echo "  health      - Check container health"
	@echo "  rebuild     - Rebuild and restart (clean build)"
	@echo "  open        - Open application in browser"
	@echo "  env-setup   - Create .env file from example"
	@echo "  env-check   - Validate environment configuration"
	@echo "  size        - Show Docker image size"

# Setup environment file
env-setup:
	@if [ ! -f .env ]; then \
		echo "Creating .env file from .env.example..."; \
		cp .env.example .env; \
		echo ".env file created. Please review and adjust settings if needed."; \
	else \
		echo ".env file already exists."; \
	fi

# Check environment configuration
env-check:
	@echo "Checking environment configuration..."
	@if [ -f .env ]; then \
		echo "✓ .env file exists"; \
		echo ""; \
		echo "Current settings:"; \
		cat .env | grep -v "^#" | grep -v "^$$"; \
	else \
		echo "✗ .env file not found. Run 'make env-setup' to create it."; \
	fi

# Build the Docker image
build: env-setup
	@echo "Building Docker image with multi-stage optimization..."
	DOCKER_BUILDKIT=1 docker-compose build --progress=plain

# Start container in detached mode
up:
	@echo "Starting container..."
	docker-compose up -d
	@echo "Application running at http://localhost:$(PORT)"

# Stop and remove container
down:
	@echo "Stopping container..."
	docker-compose down

# Restart the container
restart:
	@echo "Restarting container..."
	docker-compose restart

# View logs (follow mode)
logs:
	docker-compose logs -f

# View last 100 lines of logs
logs-tail:
	docker-compose logs --tail=100

# Open shell in running container
shell:
	docker-compose exec $(CONTAINER_NAME) /bin/bash

# Remove container and image
clean:
	@echo "Cleaning up..."
	docker-compose down -v
	docker rmi $(IMAGE_NAME) 2>/dev/null || true

# Prune all Docker resources
prune:
	@echo "Pruning Docker resources..."
	docker system prune -af --volumes

# Development mode with hot reload
dev:
	@echo "Starting in development mode..."
	@sed -i.bak 's/# - \.\/src/- \.\/src/g' docker-compose.yml 2>/dev/null || \
	 sed -i '' 's/# - \.\/src/- \.\/src/g' docker-compose.yml 2>/dev/null || true
	@$(MAKE) up
	@echo "Development mode enabled with hot reload"

# Production mode
prod:
	@echo "Starting in production mode..."
	@sed -i.bak 's/^      - \.\/src/      # - \.\/src/g' docker-compose.yml 2>/dev/null || \
	 sed -i '' 's/^      - \.\/src/      # - \.\/src/g' docker-compose.yml 2>/dev/null || true
	@$(MAKE) up

# Backup data directory
backup:
	@echo "Creating backup..."
	@mkdir -p backups
	@tar -czf backups/data-backup-$$(date +%Y%m%d-%H%M%S).tar.gz data/
	@echo "Backup created in backups/"

# Restore data directory from latest backup
restore:
	@echo "Restoring from latest backup..."
	@latest=$$(ls -t backups/data-backup-*.tar.gz 2>/dev/null | head -1); \
	if [ -n "$$latest" ]; then \
		tar -xzf "$$latest" -C .; \
		echo "Restored from $$latest"; \
	else \
		echo "No backup found"; \
	fi

# Show container status
status:
	@echo "Container status:"
	@docker-compose ps
	@echo ""
	@docker stats --no-stream $(CONTAINER_NAME) 2>/dev/null || echo "Container not running"

# Check container health
health:
	@echo "Checking container health..."
	@docker inspect --format='{{.State.Health.Status}}' $(CONTAINER_NAME) 2>/dev/null || echo "Container not running"

# Rebuild from scratch
rebuild:
	@echo "Rebuilding from scratch..."
	@$(MAKE) down
	docker-compose build --no-cache
	@$(MAKE) up

# Open in browser
open:
	@echo "Opening application in browser..."
	@command -v xdg-open >/dev/null && xdg-open http://localhost:$(PORT) || \
	 command -v open >/dev/null && open http://localhost:$(PORT) || \
	 echo "Please open http://localhost:$(PORT) in your browser"

# Quick start (build and run)
start: build up
	@echo "Application started successfully!"
	@$(MAKE) open

# Stop everything
stop: down

# Show Docker image size
size:
	@echo "Docker image sizes:"
	@docker images | grep $(IMAGE_NAME) || echo "Image not built yet"
	@echo ""
	@docker system df

# Run with custom port
run-port:
	@read -p "Enter port number (default 8501): " port; \
	port=$${port:-8501}; \
	PORT=$$port docker-compose up -d; \
	echo "Application running at http://localhost:$$port"

# View environment variables in container
env-show:
	@echo "Environment variables in container:"
	@docker-compose exec $(CONTAINER_NAME) env | grep STREAMLIT || echo "Container not running"

# Test the application
test:
	@echo "Running tests..."
	docker-compose exec $(CONTAINER_NAME) pytest || echo "Run 'make up' first"

# Quick check - build, start, and show logs
check: build up
	@sleep 5
	@$(MAKE) health
	@$(MAKE) logs-tail
