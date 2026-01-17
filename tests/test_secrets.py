"""Tests for API key management (_secrets module)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from agentic_cba_indicators.config._secrets import (
    SUPPORTED_KEYS,
    get_api_key,
    list_configured_keys,
    require_api_key,
)


class TestSupportedKeys:
    """Tests for the SUPPORTED_KEYS registry."""

    def test_supported_keys_contains_expected_services(self) -> None:
        """Verify core services are registered."""
        assert "gfw" in SUPPORTED_KEYS
        assert "anthropic" in SUPPORTED_KEYS
        assert "openai" in SUPPORTED_KEYS

    def test_supported_keys_values_are_env_var_format(self) -> None:
        """All values should be uppercase environment variable names."""
        for service, env_var in SUPPORTED_KEYS.items():
            assert env_var.isupper(), f"{service} env var should be uppercase"
            assert "_" in env_var or env_var.isalnum(), f"{service} env var invalid"


class TestGetApiKey:
    """Tests for get_api_key function."""

    def test_returns_none_when_not_set(self) -> None:
        """Returns None when environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure the env var is not set
            os.environ.pop("GFW_API_KEY", None)
            result = get_api_key("gfw")
            assert result is None

    def test_returns_key_when_set(self) -> None:
        """Returns the key value when environment variable is set."""
        with patch.dict(os.environ, {"GFW_API_KEY": "test-key-123"}):
            result = get_api_key("gfw")
            assert result == "test-key-123"

    def test_case_insensitive_service_name(self) -> None:
        """Service name lookup is case-insensitive."""
        with patch.dict(os.environ, {"GFW_API_KEY": "test-key"}):
            assert get_api_key("gfw") == "test-key"
            assert get_api_key("GFW") == "test-key"
            assert get_api_key("Gfw") == "test-key"

    def test_raises_for_unknown_service(self) -> None:
        """Raises ValueError for unregistered service names."""
        with pytest.raises(ValueError, match="Unknown service"):
            get_api_key("unknown_service")

    def test_error_message_lists_supported_services(self) -> None:
        """Error message includes list of supported services."""
        with pytest.raises(ValueError) as exc_info:
            get_api_key("invalid")

        error_msg = str(exc_info.value)
        assert "gfw" in error_msg
        assert "anthropic" in error_msg


class TestRequireApiKey:
    """Tests for require_api_key function."""

    def test_returns_key_when_set(self) -> None:
        """Returns the key value when configured."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-123"}):
            result = require_api_key("anthropic")
            assert result == "sk-ant-123"

    def test_raises_when_not_set(self) -> None:
        """Raises ValueError when key is not configured."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GFW_API_KEY", None)
            with pytest.raises(ValueError, match="API key not configured"):
                require_api_key("gfw")

    def test_error_includes_env_var_name(self) -> None:
        """Error message includes the environment variable to set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GFW_API_KEY", None)
            with pytest.raises(ValueError) as exc_info:
                require_api_key("gfw")

            assert "GFW_API_KEY" in str(exc_info.value)

    def test_raises_for_unknown_service(self) -> None:
        """Raises ValueError for unregistered service names."""
        with pytest.raises(ValueError, match="Unknown service"):
            require_api_key("nonexistent")


class TestListConfiguredKeys:
    """Tests for list_configured_keys function."""

    def test_returns_dict_of_all_services(self) -> None:
        """Returns a dict with all supported services."""
        result = list_configured_keys()
        assert isinstance(result, dict)
        for service in SUPPORTED_KEYS:
            assert service in result

    def test_shows_true_for_configured_keys(self) -> None:
        """Services with env vars set show True."""
        with patch.dict(
            os.environ, {"GFW_API_KEY": "test", "OPENAI_API_KEY": "sk-123"}
        ):
            result = list_configured_keys()
            assert result["gfw"] is True
            assert result["openai"] is True

    def test_shows_false_for_missing_keys(self) -> None:
        """Services without env vars set show False."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear all supported keys
            for env_var in SUPPORTED_KEYS.values():
                os.environ.pop(env_var, None)

            result = list_configured_keys()
            # At least some should be False
            assert any(not configured for configured in result.values())


class TestDotenvIntegration:
    """Tests for optional python-dotenv integration."""

    def test_dotenv_not_required(self) -> None:
        """Module works without python-dotenv installed."""
        # This test passes if the module imports without error
        # The actual dotenv loading is a no-op if not installed
        from agentic_cba_indicators.config import _secrets

        # Reset the flag to test loading behavior
        _secrets._dotenv_loaded = False
        _secrets._try_load_dotenv()
        # Should complete without error regardless of dotenv availability
        assert _secrets._dotenv_loaded is True
