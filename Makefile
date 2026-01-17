# Makefile for agentic-cba-indicators
# Use 'make help' to see all available commands

.PHONY: help
help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install:  ## Install package and dependencies
	uv sync

.PHONY: lint
lint:  ## Run linters (ruff and mypy)
	@echo "Running ruff check..."
	uv run ruff check src tests scripts
	@echo "\nRunning mypy..."
	uv run mypy src

.PHONY: format
format:  ## Format code with ruff
	@echo "Running ruff format..."
	uv run ruff format src tests scripts

.PHONY: format-check
format-check:  ## Check if code is formatted correctly
	@echo "Checking ruff format..."
	uv run ruff format --check src tests scripts

.PHONY: fix
fix:  ## Auto-fix linting issues
	uv run ruff check --fix src tests scripts
	uv run ruff format src tests scripts

.PHONY: test
test:  ## Run tests with pytest
	uv run pytest tests/ -v

.PHONY: test-cov
test-cov:  ## Run tests with coverage report
	uv run pytest tests/ --cov=agentic_cba_indicators --cov-report=html --cov-report=term

.PHONY: clean
clean:  ## Clean up generated files
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

.PHONY: pre-commit-install
pre-commit-install:  ## Install pre-commit hooks
	uv run pre-commit install

.PHONY: pre-commit-run
pre-commit-run:  ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

.PHONY: ingest
ingest:  ## Ingest CBA indicators into knowledge base
	python scripts/ingest_excel.py

.PHONY: ingest-usecases
ingest-usecases:  ## Ingest use case projects
	python scripts/ingest_usecases.py

.PHONY: run
run:  ## Run the CLI
	agentic-cba

.PHONY: all
all: format lint test  ## Format, lint, and test
