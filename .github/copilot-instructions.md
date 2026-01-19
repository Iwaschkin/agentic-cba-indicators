# Agentic CBA Indicators - AI Coding Instructions

## Project Overview

A CLI chatbot that queries weather, climate, socio-economic data, and **CBA ME Indicators** using the **Strands Agents SDK**. Supports multiple AI providers: **Ollama** (local), **Anthropic**, **OpenAI**, **AWS Bedrock**, and **Google Gemini**. Includes a local RAG knowledge base using ChromaDB for semantic search over indicator and measurement method data.

## GitHub Copilot Instructions

## Priority Guidelines

When generating code for this repository:

1. **Version Compatibility**: Use Python 3.11+ features only. Respect versions in pyproject.toml.
2. **Context Files**: Prioritize patterns in this file, CODE_QUALITY.md, and CONTRIBUTING.md.
3. **Codebase Patterns**: Follow established patterns in src/agentic_cba_indicators/ and tests/.
4. **Architectural Consistency**: Keep the monolithic CLI + modular tools architecture.
5. **Code Quality**: Prioritize maintainability, performance, security, and testability.

## Technology Versions (Detected)

- **Python**: >=3.11 (pyproject.toml, .python-version)
- **Package Manager**: uv
- **Core Libraries**:
  - strands-agents[ollama] >= 1.22.0
  - chromadb >= 1.4.1
  - httpx >= 0.28.1
  - pandas >= 2.3.3
  - openpyxl >= 3.1.5
  - platformdirs >= 4.0.0
  - pyyaml >= 6.0.3
  - streamlit >= 1.40.0
- **Quality Tooling**: ruff (lint/format), pyright, pytest, pre-commit

Do not use APIs or syntax beyond these versions.

## Architecture & Structure

- **Style**: Monolithic CLI app with modular tool and service modules.
- **Layout**: src/agentic_cba_indicators/ (src layout), tests/ for pytest.
- **Boundaries**:
  - CLI wiring in cli.py
  - Configuration in config/
  - Tools in tools/
  - Shared utilities in tools/_*.py
  - Logging in logging_config.py
  - Security in security.py
  - Observability in observability.py, audit.py

## Codebase Patterns to Follow

### Imports & Typing
- Use absolute imports within the package.
- Use type hints everywhere; prefer typing.Any only when necessary.
- Use TYPE_CHECKING for optional imports.

### Tool Design
- Use `@tool` from strands.
- Tools return **string** outputs.
- Include full docstrings with Args/Returns in Google-style format.
- For external APIs, use tools/_http.py helpers and return `format_error()` on APIError.
- Prefer thread-safe caches with TTLCache + threading.Lock.

### Error Handling
- Use APIError for HTTP failures.
- Use `format_error(error, context)` to sanitize and display errors.
- Error categories are added via `classify_error()` and should be preserved.

### Logging
- Use `get_logger(__name__)`.
- Structured JSON logging is supported; avoid custom logging formats.
- Correlation IDs are set per user request in cli.py.

### Caching
- Use TTLCache for repeated queries (KB and HTTP caching patterns).
- Keep caches bounded and thread-safe.

### Knowledge Base
- Use ChromaDB PersistentClient with thread-safe singleton.
- Respect schema versioning and ingestion timestamps in metadata.
- Use embedding helper from tools/_embedding.py.

## Documentation Requirements

- Docstrings are required for public functions.
- Follow existing Google-style docstrings.
- Keep module-level docstrings where present.

## Testing Approach

- Use pytest.
- Tests are in tests/test_*.py.
- Use fixtures and monkeypatch where appropriate.
- Match existing assertion style and naming.

## Tooling Commands

- Ruff: `uv run ruff check src tests scripts`
- Ruff format: `uv run ruff format src tests scripts`
- Pyright: `uv run pyright`
- Pre-commit: `uv run pre-commit run --all-files`

## Project-Specific Guidance

- Do not invent new patterns; match the surrounding module style.
- Keep functions small and single-purpose.
- Preserve existing public APIs and signatures unless explicitly asked.
- Keep system prompt and tool definitions in prompts/ and tools/.
