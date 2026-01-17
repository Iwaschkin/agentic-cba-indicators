param(
    [Parameter(Position = 0)]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host "Available commands:" -ForegroundColor Cyan
    Write-Host "  install          Install dependencies (uv sync)"
    Write-Host "  lint             Run ruff + mypy"
    Write-Host "  format           Format with ruff + black"
    Write-Host "  format-check     Check formatting"
    Write-Host "  fix              Auto-fix lint issues"
    Write-Host "  test             Run pytest"
    Write-Host "  test-cov         Run pytest with coverage"
    Write-Host "  clean            Remove caches/build artifacts"
    Write-Host "  pre-commit-install  Install git hooks"
    Write-Host "  pre-commit-run      Run hooks on all files"
    Write-Host "  ingest           Ingest indicators"
    Write-Host "  ingest-usecases  Ingest use cases"
    Write-Host "  run              Run the CLI"
    Write-Host "  all              Format, lint, test"
}

switch ($Command) {
    "help" { Show-Help }
    "install" { uv sync }
    "lint" {
        Write-Host "Running ruff check..."
        uv run ruff check src tests scripts
        Write-Host "`nRunning mypy..."
        uv run mypy src
    }
    "format" {
        Write-Host "Running ruff format..."
        uv run ruff format src tests scripts
    }
    "format-check" {
        Write-Host "Checking ruff format..."
        uv run ruff format --check src tests scripts
    }
    "fix" {
        uv run ruff check --fix src tests scripts
        uv run ruff format src tests scripts
    }
    "test" { uv run pytest tests/ -v }
    "test-cov" { uv run pytest tests/ --cov=agentic_cba_indicators --cov-report=html --cov-report=term }
    "clean" {
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .pytest_cache, .mypy_cache, .ruff_cache, htmlcov, .coverage, dist, build
        Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    "pre-commit-install" { uv run pre-commit install }
    "pre-commit-run" { uv run pre-commit run --all-files }
    "ingest" { python scripts/ingest_excel.py }
    "ingest-usecases" { python scripts/ingest_usecases.py }
    "run" { agentic-cba }
    "all" {
        & $PSCommandPath format
        & $PSCommandPath lint
        & $PSCommandPath test
        Write-Host "`n✓ All checks passed!" -ForegroundColor Green
    }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
