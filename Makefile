.PHONY: help install test lint format clean docker-up docker-down docker-logs run dev

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies with uv
	@echo "Installing dependencies..."
	uv sync --all-extras
	@echo "✓ Dependencies installed"

test: ## Run tests with pytest
	@echo "Running tests..."
	uv run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
	@echo "✓ Tests complete. Coverage report: htmlcov/index.html"

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	uv run pytest tests/unit/ -v
	@echo "✓ Unit tests complete"

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	uv run pytest tests/integration/ -v
	@echo "✓ Integration tests complete"

lint: ## Run code quality checks (flake8, mypy)
	@echo "Running linters..."
	uv run flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503
	uv run mypy src/ --ignore-missing-imports
	@echo "✓ Linting complete"

format: ## Format code with black and isort
	@echo "Formatting code..."
	uv run black src/ tests/ --line-length=100
	uv run isort src/ tests/ --profile=black
	@echo "✓ Code formatted"

format-check: ## Check code formatting without changes
	@echo "Checking code format..."
	uv run black src/ tests/ --check --line-length=100
	uv run isort src/ tests/ --check-only --profile=black
	@echo "✓ Format check complete"

clean: ## Clean build artifacts and caches
	@echo "Cleaning..."
	rm -rf .venv/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✓ Cleaned"

docker-build: ## Build Docker images
	@echo "Building Docker images..."
	docker-compose build
	@echo "✓ Docker images built"

docker-up: ## Start all services with Docker Compose
	@echo "Starting services..."
	docker-compose up -d
	@echo "✓ Services started"
	@echo ""
	@echo "🎮 Chess demo available at: http://localhost:3000"
	@echo "📡 API docs available at: http://localhost:8000/docs"
	@echo "📊 Metrics available at: http://localhost:8000/metrics"
	@echo ""
	@echo "Run 'make docker-logs' to see logs"
	@echo "Run 'make docker-down' to stop services"

docker-down: ## Stop all services
	@echo "Stopping services..."
	docker-compose down
	@echo "✓ Services stopped"

docker-logs: ## Show Docker logs
	docker-compose logs -f

docker-restart: ## Restart all services
	@echo "Restarting services..."
	docker-compose restart
	@echo "✓ Services restarted"

run: ## Run the chess environment server locally
	@echo "Starting chess environment server..."
	uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
	@echo "✓ Server started at http://localhost:8000"

dev: ## Run development server with auto-reload
	@echo "Starting development server..."
	uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
	@echo "✓ Dev server started at http://localhost:8000"

docs-serve: ## Serve documentation locally
	@echo "Serving documentation..."
	uv run mkdocs serve
	@echo "✓ Docs available at http://localhost:8001"

docs-build: ## Build documentation site
	@echo "Building documentation..."
	uv run mkdocs build
	@echo "✓ Documentation built to site/"

setup: install ## Complete setup (install dependencies)
	@echo "✓ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Run 'make test' to verify installation"
	@echo "  3. Run 'make docker-up' to start the demo"

verify: format-check lint test ## Run all checks (format, lint, test)
	@echo "✓ All checks passed!"

.PHONY: install test test-unit test-integration lint format format-check clean
.PHONY: docker-build docker-up docker-down docker-logs docker-restart
.PHONY: run dev docs-serve docs-build setup verify
