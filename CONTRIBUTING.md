# Contributing to Agentic CBA Indicators

Thank you for your interest in contributing! This guide covers how to add new tools to the chatbot.

## Adding New Tools

### 1. Create the Tool File

Create a new file in `src/agentic_cba_indicators/tools/`:

```python
# src/agentic_cba_indicators/tools/my_tools.py
"""My domain tools - brief description of the domain."""

from strands import tool


@tool
def my_tool_name(param1: str, param2: int = 10) -> str:
    """
    Brief one-line description shown in tool listings.

    More detailed description of what the tool does, when to use it,
    and any important context the LLM should know.

    Args:
        param1: Description of first parameter
        param2: Description with default (default: 10)

    Returns:
        Description of what the tool returns
    """
    # Implementation here
    return f"Result for {param1} with {param2}"
```

### 2. Docstring Requirements

The docstring is **critical** - it's what the LLM uses to decide when to call your tool.

- **First line**: Brief summary (shown in `list_tools()` output)
- **Body**: Detailed usage guidance for the LLM
- **Args**: Document each parameter with types
- **Returns**: Describe the output format

### 3. Register in `__init__.py`

Add your tool to `src/agentic_cba_indicators/tools/__init__.py`:

```python
# Import your tool
from agentic_cba_indicators.tools.my_tools import my_tool_name

# Add to __all__
__all__ = [
    # ... existing tools ...
    "my_tool_name",
]

# Add to appropriate tool list
REDUCED_TOOLS: list[Callable[..., str]] = [
    # ... 24 core tools for small context windows ...
]

FULL_TOOLS: list[Callable[..., str]] = [
    # ... all 62+ tools including yours ...
    my_tool_name,
]
```

**REDUCED_TOOLS vs FULL_TOOLS:**
- `REDUCED_TOOLS` (24 tools): Core tools for providers with small context windows
- `FULL_TOOLS` (62+ tools): Complete set for large context providers

Only add to `REDUCED_TOOLS` if the tool is essential for basic functionality.

### 4. Add Tool Category Mapping

Update `_TOOL_CATEGORIES` in `src/agentic_cba_indicators/tools/_help.py`:

```python
_TOOL_CATEGORIES: dict[str, tuple[str, list[str]]] = {
    # ... existing categories ...
    "my_category": (
        "Human-Readable Category Name",
        ["my_tool", "keyword1", "keyword2"],  # Tool name prefixes/keywords
    ),
}
```

Keywords are used by `list_tools_by_category()` and `search_tools()` to help the agent find tools.

### ToolContext Usage Policy

`ToolContext` is reserved for **internal help tools** in `tools/_help.py`.
External tools should **not** require `ToolContext` unless absolutely necessary.
If a new tool requires runtime context, document the rationale and add tests.

### 5. Create Tests

Add tests in `tests/test_tools_<domain>.py`:

```python
# tests/test_tools_my_domain.py
"""Tests for my domain tools."""

import pytest
from agentic_cba_indicators.tools import my_tool_name


def test_my_tool_basic():
    """Test basic functionality."""
    result = my_tool_name("test", 5)
    assert "test" in result
    assert "5" in result


def test_my_tool_edge_cases():
    """Test edge cases."""
    result = my_tool_name("", 0)
    assert isinstance(result, str)
```

### 6. Verify

Run the test suite:

```bash
# Run all tests
uv run pytest

# Run just your tests
uv run pytest tests/test_tools_my_domain.py -v

# Check types
uv run pyright src/agentic_cba_indicators/tools/my_tools.py

# Check style
uv run ruff check src/agentic_cba_indicators/tools/my_tools.py
```

## Tool Development Patterns

### External API Tools

For tools calling external APIs, use the shared HTTP client:

```python
from agentic_cba_indicators.tools._http import fetch_json, APIError, format_error

@tool
def my_api_tool(query: str) -> str:
    """Call external API."""
    try:
        data = fetch_json(
            "https://api.example.com/endpoint",
            params={"q": query},
        )
        return f"Found: {data['result']}"
    except APIError as e:
        return format_error(e, "fetching data")
```

### Tools with Geocoding

For location-based tools:

```python
from agentic_cba_indicators.tools._geo import geocode_city

@tool
def my_location_tool(city: str) -> str:
    """Get data for a city."""
    location = geocode_city(city)
    if not location:
        return f"Could not find location: {city}"

    # Use location["latitude"], location["longitude"], etc.
    return f"Data for {location['name']}, {location['country']}"
```

### Tools Requiring Secrets

For tools needing API keys:

```python
from agentic_cba_indicators.secrets import get_secret

@tool
def my_authenticated_tool(query: str) -> str:
    """Tool requiring API key."""
    api_key = get_secret("MY_SERVICE_API_KEY")
    if not api_key:
        return "MY_SERVICE_API_KEY not configured. Set in .env or environment."

    # Use api_key in requests...
```

## Code Standards

- **Type hints**: Required on all function signatures
- **Docstrings**: Google style, required for all public functions
- **Imports**: Use absolute imports, sorted by ruff
- **Error handling**: Catch specific exceptions, never bare `except:`
- **Logging**: Use `get_logger(__name__)` for debug output

## Questions?

Open an issue or check existing tools in `src/agentic_cba_indicators/tools/` for examples.
