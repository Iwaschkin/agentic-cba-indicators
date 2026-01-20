"""
Prompt loading utilities for agentic-cba-indicators.

Loads system prompts from bundled package resources.
"""

from __future__ import annotations

import importlib.resources
import os
from functools import lru_cache


@lru_cache(maxsize=4)
def load_prompt(name: str) -> str:
    """
    Load a prompt file from the bundled prompts directory.

    Args:
        name: Name of the prompt file (without .md extension)

    Returns:
        Contents of the prompt file

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    resource_name = f"{name}.md"
    try:
        files = importlib.resources.files("agentic_cba_indicators.prompts")
        return (files / resource_name).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found: {resource_name}") from None


def get_system_prompt(prompt_name: str | None = None) -> str:
    """
    Load the default system prompt.

    Args:
        prompt_name: Optional prompt name override (without .md extension).
            If not provided, uses AGENTIC_CBA_PROMPT environment variable,
            falling back to "system_prompt_minimal".

    Returns:
        The system prompt content
    """
    resolved_name = prompt_name or os.environ.get(
        "AGENTIC_CBA_PROMPT", "system_prompt_minimal"
    )
    return load_prompt(resolved_name)


def clear_prompt_cache() -> None:
    """Clear cached prompts. Useful for development/testing."""
    load_prompt.cache_clear()
