"""Tests for the paths module."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class TestGetDataDir:
    """Tests for get_data_dir function."""

    def test_uses_env_var_when_set(self, tmp_path: Path) -> None:
        """Should use AGENTIC_CBA_DATA_DIR when set."""
        from agentic_cba_indicators.paths import clear_path_cache, get_data_dir

        env_path = tmp_path / "custom_data"
        os.environ["AGENTIC_CBA_DATA_DIR"] = str(env_path)
        clear_path_cache()

        result = get_data_dir()

        assert result == env_path
        assert result.exists()

        # Cleanup
        os.environ.pop("AGENTIC_CBA_DATA_DIR")
        clear_path_cache()

    def test_creates_directory(self, temp_data_dir: Path) -> None:
        """Should create the data directory if it doesn't exist."""
        from agentic_cba_indicators.paths import get_data_dir

        result = get_data_dir()
        assert result.exists()
        assert result.is_dir()


class TestGetKbPath:
    """Tests for get_kb_path function."""

    def test_returns_kb_data_subdir(self, temp_data_dir: Path) -> None:
        """Should return kb_data subdirectory of data dir."""
        from agentic_cba_indicators.paths import get_kb_path

        result = get_kb_path()

        assert result.name == "kb_data"
        assert result.parent == temp_data_dir
        assert result.exists()


class TestGetUserConfigPath:
    """Tests for get_user_config_path function."""

    def test_returns_providers_yaml_path(self, temp_config_dir: Path) -> None:
        """Should return path to providers.yaml in config dir."""
        from agentic_cba_indicators.paths import get_user_config_path

        result = get_user_config_path()

        assert result.name == "providers.yaml"
        assert result.parent == temp_config_dir
