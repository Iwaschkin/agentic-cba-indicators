"""Tests for the config module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


class TestLoadConfig:
    """Tests for load_config function."""

    def test_loads_from_explicit_path(self, sample_config: Path) -> None:
        """Should load config from explicit path."""
        from agentic_cba_indicators.config import load_config

        config = load_config(sample_config)

        assert config["active_provider"] == "ollama"
        assert "providers" in config
        assert "ollama" in config["providers"]

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError for missing config."""
        from agentic_cba_indicators.config import load_config

        missing = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_config(missing)

    def test_expands_env_vars(self, temp_config_dir: Path) -> None:
        """Should expand ${ENV_VAR} patterns in config."""
        import os

        from agentic_cba_indicators.config import load_config

        # Create config with env var
        config_content = """
active_provider: anthropic
providers:
  anthropic:
    api_key: ${TEST_API_KEY}
    model_id: claude-3-haiku
"""
        config_file = temp_config_dir / "providers.yaml"
        config_file.write_text(config_content)

        os.environ["TEST_API_KEY"] = "sk-test-12345"
        try:
            config = load_config(config_file)
            assert config["providers"]["anthropic"]["api_key"] == "sk-test-12345"
        finally:
            os.environ.pop("TEST_API_KEY", None)


class TestGetProviderConfig:
    """Tests for get_provider_config function."""

    def test_extracts_active_provider(self, sample_config: Path) -> None:
        """Should return config for the active provider."""
        from agentic_cba_indicators.config import get_provider_config, load_config

        config = load_config(sample_config)
        provider_config = get_provider_config(config)

        assert provider_config.name == "ollama"
        assert provider_config.model_id == "llama3.1:latest"
        assert provider_config.temperature == 0.1

    def test_raises_on_unknown_provider(self, temp_config_dir: Path) -> None:
        """Should raise ValueError for unknown provider."""
        from agentic_cba_indicators.config import get_provider_config, load_config

        config_content = """
active_provider: unknown_provider
providers:
  ollama:
    model_id: test
"""
        config_file = temp_config_dir / "providers.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        with pytest.raises(ValueError, match="unknown_provider"):
            get_provider_config(config)


class TestGetAgentConfig:
    """Tests for get_agent_config function."""

    def test_extracts_agent_settings(self, sample_config: Path) -> None:
        """Should return agent configuration."""
        from agentic_cba_indicators.config import get_agent_config, load_config

        config = load_config(sample_config)
        agent_config = get_agent_config(config)

        assert agent_config.tool_set == "reduced"
        assert agent_config.conversation_window == 5

    def test_uses_defaults_when_missing(self, temp_config_dir: Path) -> None:
        """Should use defaults when agent section is missing."""
        from agentic_cba_indicators.config import get_agent_config, load_config

        config_content = """
active_provider: ollama
providers:
  ollama:
    model_id: test
"""
        config_file = temp_config_dir / "providers.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)
        agent_config = get_agent_config(config)

        assert agent_config.tool_set == "reduced"  # default
        assert agent_config.conversation_window == 5  # default
