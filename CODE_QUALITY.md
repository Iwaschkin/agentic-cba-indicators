# Code Quality Setup

This document describes the code quality tools configured for the `agentic-cba-indicators` project.

## Tools Configured

### 1. **Ruff** - Fast Python Linter & Formatter
- ✅ Replaces: Flake8, isort, pyupgrade, and more
- ✅ Speed: 10-100x faster than traditional tools
- ✅ Black-compatible formatting built-in

**Rules enabled:**
- `E/W` - PEP 8 style errors and warnings
- `F` - Pyflakes (imports, undefined names)
- `I` - Import sorting
- `B` - Bugbear (common bugs)
- `C4` - Better comprehensions
- `UP` - Modern Python syntax
- `ARG` - Unused arguments
- `SIM` - Code simplifications
- `RUF` - Ruff-specific rules
- `TCH` - Type-checking imports
- `PTH` - Use pathlib
- `ERA` - Remove commented code
- `PERF` - Performance anti-patterns

**Run:**
```bash
uv run ruff check src tests scripts          # Check
uv run ruff check src tests scripts --fix    # Auto-fix
uv run ruff format src tests scripts         # Format
```

### 2. **Ruff Format** (replaces Black)
- ✅ Built into ruff - same tool for linting and formatting
- ✅ Black-compatible formatting
- ✅ 88 character line length

**Run:**
```bash
uv run ruff format src tests scripts         # Format
uv run ruff format --check src tests scripts # Check only
```

### 3. **mypy** - Static Type Checker
- ✅ Strict mode enabled
- ✅ Catches type errors before runtime
- ✅ Excluded from tests for flexibility

**Run:**
```bash
uv run mypy src
```

### 4. **Pre-commit Hooks**
Automatically run quality checks before each commit.

**Install once:**
```bash
uv run pre-commit install
```

**What runs on commit:**
1. Ruff linting with auto-fix
2. Ruff formatting
3. mypy type checking
4. Trailing whitespace removal
5. YAML/TOML validation
6. Large file detection
7. Merge conflict detection

**Manual run:**
```bash
uv run pre-commit run --all-files
```

## Quick Commands (Makefile / dev.ps1)

**Linux/Mac (Makefile):**
```bash
make help              # Show all commands
make install           # Install dependencies
make lint              # Run ruff + mypy
make format            # Format with ruff
make fix               # Auto-fix issues
make test              # Run pytest
make test-cov          # Run with coverage
make all               # Format + lint + test
make pre-commit-run    # Run all pre-commit hooks
```

**Windows (PowerShell):**
```powershell
.\dev.ps1 help           # Show all commands
.\dev.ps1 install        # Install dependencies
.\dev.ps1 lint           # Run ruff + mypy
.\dev.ps1 format         # Format with ruff
.\dev.ps1 fix            # Auto-fix issues
.\dev.ps1 test           # Run pytest
.\dev.ps1 test-cov       # Run with coverage
.\dev.ps1 all            # Format + lint + test
.\dev.ps1 pre-commit-run # Run all pre-commit hooks
```

## Current Status

**After setup:**
- ✅ All ruff checks passing
- ✅ All mypy checks passing
- ✅ All 11 tests passing
- ✅ Pre-commit hooks installed

## Remaining Issues

Most remaining ruff warnings are **optional improvements**:

### Safe to Ignore
- `ARG005` - Unused lambda arguments in soil texture classifiers (intentional design)
- `B905` - Missing `strict=` in zip() calls (would need testing to ensure safety)
- `C401` - Generator → set comprehension (micro-optimization)
- `PERF401` - List append → extend (micro-optimization)

### Worth Fixing Later
- `B904` - Exception chaining (`raise ... from err`)
- `B007` - Unused loop variables (rename to `_var`)
- `SIM` - Code simplifications

## Integration with AI Tools

The configuration optimizes for **AI readability and correctness**:

1. **Consistent formatting** - Black + Ruff ensure uniform style
2. **Type annotations** - mypy strict mode catches type errors
3. **Import organization** - Automatic sorting and grouping
4. **Modern Python** - pyupgrade ensures latest idioms
5. **Bug prevention** - Bugbear catches common mistakes
6. **Performance** - PERF rules highlight anti-patterns

## Configuration Files

- `pyproject.toml` - Tool configuration (ruff, black, mypy, pytest)
- `.pre-commit-config.yaml` - Pre-commit hook definitions
- `Makefile` - Convenient command shortcuts

## For New Contributors

```bash
# Initial setup
git clone <repo>
cd agentic-cba-indicators
uv sync
uv run pre-commit install

# Before committing
make all

# Or let pre-commit handle it automatically
git commit -m "Your changes"  # Hooks run automatically
```

## CI/CD Integration

If you add GitHub Actions later:

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync
      - run: uv run ruff check src tests scripts
      - run: uv run ruff format --check src tests scripts
      - run: uv run black --check src tests scripts
      - run: uv run mypy src
      - run: uv run pytest
```
