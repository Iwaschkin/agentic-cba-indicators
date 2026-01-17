"""Tests for the paths module."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest  # noqa: TC002 - pytest is used at runtime for fixture types

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


class TestPathValidation:
    """Tests for path security validation."""

    def test_logs_warning_for_traversal_pattern(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should log warning when path contains traversal patterns."""
        import logging

        from agentic_cba_indicators.paths import clear_path_cache, get_data_dir

        # Path with .. pattern (will be normalized)
        env_path = str(tmp_path / "foo" / ".." / "custom_data")
        os.environ["AGENTIC_CBA_DATA_DIR"] = env_path
        clear_path_cache()

        with caplog.at_level(logging.WARNING):
            result = get_data_dir()

        # Should log warning about '..' pattern
        assert any(".." in record.message for record in caplog.records)
        # But should still resolve to valid absolute path
        assert result.is_absolute()
        assert result.exists()

        # Cleanup
        os.environ.pop("AGENTIC_CBA_DATA_DIR")
        clear_path_cache()

    def test_normalizes_traversal_sequences(self, tmp_path: Path) -> None:
        """Should normalize path traversal sequences away."""
        from agentic_cba_indicators.paths import clear_path_cache, get_data_dir

        # Path with traversal that resolves to tmp_path/custom
        env_path = str(tmp_path / "foo" / ".." / "custom")
        os.environ["AGENTIC_CBA_DATA_DIR"] = env_path
        clear_path_cache()

        result = get_data_dir()

        # Should resolve to tmp_path/custom (normalized)
        assert result == (tmp_path / "custom")
        assert ".." not in str(result)

        # Cleanup
        os.environ.pop("AGENTIC_CBA_DATA_DIR")
        clear_path_cache()

    def test_expands_user_home(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should expand ~ to user home directory."""
        from agentic_cba_indicators.paths import clear_path_cache, get_data_dir

        # Use tmp_path as fake home
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
        os.environ["AGENTIC_CBA_DATA_DIR"] = "~/custom_data"
        clear_path_cache()

        result = get_data_dir()

        # Should expand ~ to home (tmp_path in this test)
        assert result.is_absolute()
        assert "~" not in str(result)

        # Cleanup
        os.environ.pop("AGENTIC_CBA_DATA_DIR")
        clear_path_cache()


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
