"""
Model Provider Factory

Loads configuration from YAML files and creates the appropriate Strands model
provider (Ollama, Anthropic, OpenAI, Bedrock, or Gemini).
"""

from __future__ import annotations

import importlib.resources
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from agentic_cba_indicators.paths import get_user_config_path

logger = logging.getLogger(__name__)


class ProviderCreationError(Exception):
    """Raised when model provider creation fails.

    This exception sanitizes the underlying error to avoid leaking credentials.
    """


# Whitelist of allowed environment variable names for config expansion.
# This prevents potential injection attacks where an attacker with config
# file access could exfiltrate arbitrary environment variables.
ALLOWED_ENV_VARS = frozenset(
    {
        # API keys for supported providers
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "OLLAMA_API_KEY",
        # AWS credentials (for Bedrock)
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
        # Ollama configuration
        "OLLAMA_HOST",
        # Common proxy settings (for corporate environments)
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
    }
)


@dataclass
class ProviderConfig:
    """Configuration for a model provider."""

    name: str
    model_id: str
    temperature: float = 0.1
    max_tokens: int | None = None
    options: dict[str, Any] = field(default_factory=dict)

    # Provider-specific fields
    host: str | None = None  # Ollama
    api_key: str | None = None  # Anthropic, OpenAI, Gemini
    base_url: str | None = None  # OpenAI (custom endpoints)
    region_name: str | None = None  # Bedrock
    top_p: float | None = None  # Gemini (sampling)


@dataclass
class AgentConfig:
    """Configuration for the agent."""

    tool_set: str = "reduced"  # "reduced" or "full"
    conversation_window: int = 5  # Legacy: message count for SlidingWindow
    context_budget: int | None = None  # Token budget (None = use conversation_window)
    prompt_name: str = "system_prompt_minimal"  # Prompt file name without extension
    parallel_tool_calls: bool = False  # Enable parallel tool execution helper


def _expand_env_vars(value: Any) -> Any:
    """Recursively expand ${ENV_VAR} patterns in config values.

    Only variables in ALLOWED_ENV_VARS whitelist will be expanded.
    Attempts to expand non-whitelisted variables log a warning and expand to empty string.
    """
    if isinstance(value, str):
        # Match ${VAR_NAME} pattern
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, value)
        for var_name in matches:
            if var_name not in ALLOWED_ENV_VARS:
                logger.warning(
                    "Attempted to expand non-whitelisted environment variable '%s'. "
                    "Only these variables are allowed: %s",
                    var_name,
                    ", ".join(sorted(ALLOWED_ENV_VARS)),
                )
                # Replace with empty string for security
                value = value.replace(f"${{{var_name}}}", "")
            else:
                env_value = os.environ.get(var_name, "")
                value = value.replace(f"${{{var_name}}}", env_value)
        return value
    elif isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    return value


def load_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """
    Load provider configuration from YAML file.

    Resolution order:
    1. Explicit config_path argument
    2. User config: ~/.config/agentic-cba-indicators/providers.yaml (or platform equivalent)
    3. Bundled default: agentic_cba_indicators/config/providers.yaml

    Args:
        config_path: Path to config file. If None, searches user config then bundled.

    Returns:
        Parsed and environment-expanded configuration dictionary
    """
    if config_path is not None:
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
    else:
        # Check user config first
        user_config = get_user_config_path()
        if user_config.exists():
            config_path = user_config
        else:
            # Fall back to bundled config
            try:
                files = importlib.resources.files("agentic_cba_indicators.config")
                bundled = files / "providers.yaml"
                # Read directly from package resources
                content = bundled.read_text(encoding="utf-8")
                config = yaml.safe_load(content)
                if not isinstance(config, dict):
                    raise ValueError("Bundled config is empty or invalid")
                config = _expand_env_vars(config)
                _validate_config(config)
                return config
            except Exception as e:
                raise FileNotFoundError(
                    f"No config file found. Create one at: {user_config}"
                ) from e

    with Path(config_path).open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("Config file is empty or invalid YAML")

    # Expand environment variables
    config = _expand_env_vars(config)
    _validate_config(config)
    return config


def _validate_config(config: dict[str, Any]) -> None:
    """Validate configuration schema for required fields and types."""
    if not isinstance(config, dict):
        raise ValueError("Config must be a mapping")

    active = config.get("active_provider")
    providers = config.get("providers")

    if not isinstance(active, str) or not active:
        raise ValueError("Config must include 'active_provider' as a non-empty string")

    if not isinstance(providers, dict) or not providers:
        raise ValueError("Config must include 'providers' mapping")

    if active not in providers:
        raise ValueError(
            f"Active provider '{active}' not found in providers: {list(providers.keys())}"
        )

    for name, provider_cfg in providers.items():
        if not isinstance(provider_cfg, dict):
            raise ValueError(f"Provider '{name}' configuration must be a mapping")
        model_id = provider_cfg.get("model_id")
        if not isinstance(model_id, str) or not model_id:
            raise ValueError(f"Provider '{name}' must define a non-empty 'model_id'")
        top_p = provider_cfg.get("top_p")
        if top_p is not None and not isinstance(top_p, (int, float)):
            raise ValueError(f"Provider '{name}' top_p must be a number if set")

    agent_cfg = config.get("agent", {})
    if agent_cfg is not None:
        if not isinstance(agent_cfg, dict):
            raise ValueError("Agent config must be a mapping if provided")

        tool_set = agent_cfg.get("tool_set", "reduced")
        if tool_set not in {"reduced", "full"}:
            raise ValueError("Agent 'tool_set' must be 'reduced' or 'full'")

        conversation_window = agent_cfg.get("conversation_window", 5)
        if not isinstance(conversation_window, int) or conversation_window <= 0:
            raise ValueError("Agent 'conversation_window' must be a positive integer")

        context_budget = agent_cfg.get("context_budget")
        if context_budget is not None and (
            not isinstance(context_budget, int) or context_budget <= 0
        ):
            raise ValueError("Agent 'context_budget' must be a positive integer if set")

        prompt_name = agent_cfg.get("prompt_name", "system_prompt_minimal")
        if not isinstance(prompt_name, str) or not prompt_name:
            raise ValueError("Agent 'prompt_name' must be a non-empty string")

        parallel_tool_calls = agent_cfg.get("parallel_tool_calls", False)
        if not isinstance(parallel_tool_calls, bool):
            raise ValueError("Agent 'parallel_tool_calls' must be a boolean")


def get_provider_config(config: dict[str, Any]) -> ProviderConfig:
    """
    Extract the active provider configuration.

    Args:
        config: Full configuration dictionary

    Returns:
        ProviderConfig for the active provider
    """
    active = config.get("active_provider", "ollama")
    providers = config.get("providers", {})

    if active not in providers:
        raise ValueError(
            f"Provider '{active}' not found in config. Available: {list(providers.keys())}"
        )

    provider_cfg = providers[active]

    return ProviderConfig(
        name=active,
        model_id=provider_cfg.get("model_id", ""),
        temperature=provider_cfg.get("temperature", 0.1),
        max_tokens=provider_cfg.get("max_tokens")
        or provider_cfg.get("max_output_tokens"),
        options=provider_cfg.get("options", {}),
        host=provider_cfg.get("host"),
        api_key=provider_cfg.get("api_key"),
        base_url=provider_cfg.get("base_url"),
        region_name=provider_cfg.get("region_name"),
        top_p=provider_cfg.get("top_p"),
    )


def get_agent_config(config: dict[str, Any]) -> AgentConfig:
    """Extract agent configuration."""
    agent_cfg = config.get("agent", {})
    return AgentConfig(
        tool_set=agent_cfg.get("tool_set", "reduced"),
        conversation_window=agent_cfg.get("conversation_window", 5),
        context_budget=agent_cfg.get("context_budget"),
        prompt_name=agent_cfg.get("prompt_name", "system_prompt_minimal"),
        parallel_tool_calls=agent_cfg.get("parallel_tool_calls", False),
    )


# Pattern for sanitizing potential credentials in error messages (CR-0007)
_CREDENTIAL_PATTERNS = [
    re.compile(r"api[_-]?key\s*[:=]\s*['\"]?[^\s'\"]+", re.IGNORECASE),
    re.compile(r"['\"][a-zA-Z0-9_-]{20,}['\"]"),  # Long strings in quotes (likely keys)
    re.compile(r"Bearer\s+[^\s]+", re.IGNORECASE),
]


def _sanitize_model_error(error: Exception, provider_name: str) -> str:
    """Sanitize error message to prevent credential leakage.

    Args:
        error: The original exception
        provider_name: Name of the provider for context

    Returns:
        Sanitized error message safe for logging/display
    """
    msg = str(error)
    for pattern in _CREDENTIAL_PATTERNS:
        msg = pattern.sub("[REDACTED]", msg)
    return f"{provider_name} model creation failed: {msg}"


def create_model(provider_config: ProviderConfig):
    """
    Create a Strands model instance based on provider configuration.

    Args:
        provider_config: Provider configuration

    Returns:
        Strands model instance (OllamaModel, AnthropicModel, etc.)

    Raises:
        ImportError: If provider dependencies are not installed
        ValueError: If provider is not supported
    """
    name = provider_config.name

    # --- Ollama (Local) ---
    if name == "ollama":
        from strands.models.ollama import OllamaModel

        return OllamaModel(
            host=provider_config.host or "http://localhost:11434",
            model_id=provider_config.model_id,
            temperature=provider_config.temperature,
            options=provider_config.options,
        )

    # --- Anthropic (Claude) ---
    elif name == "anthropic":
        try:
            from strands.models.anthropic import AnthropicModel
        except ImportError:
            raise ImportError(
                "Anthropic provider not installed. Run: uv add 'strands-agents[anthropic]'"
            ) from None

        if not provider_config.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or configure api_key in providers.yaml"
            )

        try:
            return AnthropicModel(
                client_args={"api_key": provider_config.api_key},
                model_id=provider_config.model_id,
                max_tokens=provider_config.max_tokens or 4096,
                params={"temperature": provider_config.temperature},
            )
        except Exception as e:
            raise ProviderCreationError(_sanitize_model_error(e, "anthropic")) from None

    # --- OpenAI (GPT) ---
    elif name == "openai":
        try:
            from strands.models.openai import OpenAIModel
        except ImportError:
            raise ImportError(
                "OpenAI provider not installed. Run: uv add 'strands-agents[openai]'"
            ) from None

        if not provider_config.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or configure api_key in providers.yaml"
            )

        client_args: dict[str, Any] = {"api_key": provider_config.api_key}
        if provider_config.base_url:
            client_args["base_url"] = provider_config.base_url

        try:
            return OpenAIModel(
                client_args=client_args,
                model_id=provider_config.model_id,
                params={
                    "max_tokens": provider_config.max_tokens or 4096,
                    "temperature": provider_config.temperature,
                },
            )
        except Exception as e:
            raise ProviderCreationError(_sanitize_model_error(e, "openai")) from None

    # --- AWS Bedrock ---
    elif name == "bedrock":
        try:
            from strands.models import BedrockModel
        except ImportError:
            raise ImportError(
                "Bedrock provider not installed. Run: uv add 'strands-agents[bedrock]'"
            ) from None

        kwargs: dict[str, Any] = {
            "model_id": provider_config.model_id,
            "temperature": provider_config.temperature,
        }

        if provider_config.region_name:
            kwargs["region_name"] = provider_config.region_name

        if provider_config.max_tokens:
            kwargs["max_tokens"] = provider_config.max_tokens

        try:
            return BedrockModel(**kwargs)
        except Exception as e:
            raise ProviderCreationError(_sanitize_model_error(e, "bedrock")) from None

    # --- Google Gemini ---
    elif name == "gemini":
        try:
            from strands.models.gemini import GeminiModel
        except ImportError:
            raise ImportError(
                "Gemini provider not installed. Run: uv add 'strands-agents[gemini]'"
            ) from None

        if not provider_config.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable "
                "or configure api_key in providers.yaml"
            )

        params: dict[str, Any] = {"temperature": provider_config.temperature}
        if provider_config.max_tokens:
            params["max_output_tokens"] = provider_config.max_tokens
        if provider_config.top_p is not None:
            params["top_p"] = provider_config.top_p

        try:
            return GeminiModel(
                client_args={"api_key": provider_config.api_key},
                model_id=provider_config.model_id,
                params=params,
            )
        except Exception as e:
            raise ProviderCreationError(_sanitize_model_error(e, "gemini")) from None

    # -------------------------------------------------------------------------
    # Unknown Provider
    # -------------------------------------------------------------------------
    else:
        supported = ["ollama", "anthropic", "openai", "bedrock", "gemini"]
        raise ValueError(f"Unknown provider: {name}. Supported: {supported}")


def print_provider_info(provider_config: ProviderConfig) -> None:
    """Print information about the active provider."""
    icons = {
        "ollama": "🦙",
        "anthropic": "🤖",
        "openai": "💚",
        "bedrock": "☁️",
        "gemini": "💎",
    }
    icon = icons.get(provider_config.name, "🔌")
    print(f"{icon} Provider: {provider_config.name}")
    print(f"   Model: {provider_config.model_id}")
    print(f"   Temperature: {provider_config.temperature}")

    if provider_config.name == "ollama":
        print(f"   Host: {provider_config.host}")
    elif provider_config.name == "bedrock":
        print(f"   Region: {provider_config.region_name or 'default'}")


# =============================================================================
# Convenience function for one-liner usage
# =============================================================================


def load_model_from_config(config_path: Path | str | None = None):
    """
    Load configuration and create model in one step.

    Args:
        config_path: Path to providers.yaml (optional)

    Returns:
        Tuple of (model, provider_config, agent_config)
    """
    config = load_config(config_path)
    provider_config = get_provider_config(config)
    agent_config = get_agent_config(config)
    model = create_model(provider_config)

    return model, provider_config, agent_config
