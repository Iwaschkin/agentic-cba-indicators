"""
Centralized path resolution for agentic-cba-indicators.

Uses platformdirs for XDG-style defaults with environment variable overrides:
- AGENTIC_CBA_DATA_DIR: Override data directory (kb_data, logs, etc.)
- AGENTIC_CBA_CONFIG_DIR: Override config directory (providers.yaml, etc.)
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import platformdirs

APP_NAME = "agentic-cba-indicators"
APP_AUTHOR = "agentic-cba"


@lru_cache(maxsize=1)
def get_data_dir() -> Path:
    """
    Get the data directory for persistent storage (kb_data, logs, etc.).

    Resolution order:
    1. AGENTIC_CBA_DATA_DIR environment variable (if set)
    2. platformdirs.user_data_dir() - XDG_DATA_HOME on Linux, AppData on Windows

    Returns:
        Path to the data directory (created if it doesn't exist)
    """
    env_dir = os.environ.get("AGENTIC_CBA_DATA_DIR")
    if env_dir:
        data_dir = Path(env_dir).expanduser().resolve()
    else:
        data_dir = Path(platformdirs.user_data_dir(APP_NAME, APP_AUTHOR))

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@lru_cache(maxsize=1)
def get_config_dir() -> Path:
    """
    Get the config directory for user configuration files.

    Resolution order:
    1. AGENTIC_CBA_CONFIG_DIR environment variable (if set)
    2. platformdirs.user_config_dir() - XDG_CONFIG_HOME on Linux, AppData on Windows

    Returns:
        Path to the config directory (created if it doesn't exist)
    """
    env_dir = os.environ.get("AGENTIC_CBA_CONFIG_DIR")
    if env_dir:
        config_dir = Path(env_dir).expanduser().resolve()
    else:
        config_dir = Path(platformdirs.user_config_dir(APP_NAME, APP_AUTHOR))

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@lru_cache(maxsize=1)
def get_cache_dir() -> Path:
    """
    Get the cache directory for temporary/cached data.

    Resolution order:
    1. AGENTIC_CBA_CACHE_DIR environment variable (if set)
    2. platformdirs.user_cache_dir() - XDG_CACHE_HOME on Linux, LocalAppData on Windows

    Returns:
        Path to the cache directory (created if it doesn't exist)
    """
    env_dir = os.environ.get("AGENTIC_CBA_CACHE_DIR")
    if env_dir:
        cache_dir = Path(env_dir).expanduser().resolve()
    else:
        cache_dir = Path(platformdirs.user_cache_dir(APP_NAME, APP_AUTHOR))

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_kb_path() -> Path:
    """
    Get the path to the knowledge base directory.

    Returns:
        Path to kb_data directory within the data directory
    """
    kb_path = get_data_dir() / "kb_data"
    kb_path.mkdir(parents=True, exist_ok=True)
    return kb_path


def get_user_config_path() -> Path:
    """
    Get the path to the user's providers.yaml config file.

    Returns:
        Path to providers.yaml in the config directory
    """
    return get_config_dir() / "providers.yaml"


def clear_path_cache() -> None:
    """Clear cached paths. Useful for testing or after environment changes."""
    get_data_dir.cache_clear()
    get_config_dir.cache_clear()
    get_cache_dir.cache_clear()
