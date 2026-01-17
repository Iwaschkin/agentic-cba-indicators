"""Pytest configuration and fixtures for agentic-cba-indicators tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Provide a temporary data directory for tests.

    Sets AGENTIC_CBA_DATA_DIR environment variable and clears path cache.
    """
    from agentic_cba_indicators.paths import clear_path_cache

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    old_value = os.environ.get("AGENTIC_CBA_DATA_DIR")
    os.environ["AGENTIC_CBA_DATA_DIR"] = str(data_dir)
    clear_path_cache()

    yield data_dir

    # Restore
    if old_value is not None:
        os.environ["AGENTIC_CBA_DATA_DIR"] = old_value
    else:
        os.environ.pop("AGENTIC_CBA_DATA_DIR", None)
    clear_path_cache()


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Provide a temporary config directory for tests.

    Sets AGENTIC_CBA_CONFIG_DIR environment variable and clears path cache.
    """
    from agentic_cba_indicators.paths import clear_path_cache

    config_dir = tmp_path / "config"
    config_dir.mkdir()

    old_value = os.environ.get("AGENTIC_CBA_CONFIG_DIR")
    os.environ["AGENTIC_CBA_CONFIG_DIR"] = str(config_dir)
    clear_path_cache()

    yield config_dir

    # Restore
    if old_value is not None:
        os.environ["AGENTIC_CBA_CONFIG_DIR"] = old_value
    else:
        os.environ.pop("AGENTIC_CBA_CONFIG_DIR", None)
    clear_path_cache()


@pytest.fixture
def sample_config(temp_config_dir: Path) -> Path:
    """Create a sample providers.yaml for testing."""
    config_content = """
active_provider: ollama

providers:
  ollama:
    host: "http://localhost:11434"
    model_id: "llama3.1:latest"
    temperature: 0.1
    options:
      num_ctx: 8192

agent:
  tool_set: reduced
  conversation_window: 5
"""
    config_file = temp_config_dir / "providers.yaml"
    config_file.write_text(config_content)
    return config_file
