"""
Model Provider Factory

Loads configuration from YAML files and creates the appropriate Strands model
provider (Ollama, Anthropic, OpenAI, Bedrock, or Gemini).
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


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


@dataclass
class AgentConfig:
    """Configuration for the agent."""

    tool_set: str = "reduced"  # "reduced" or "full"
    conversation_window: int = 5


def _expand_env_vars(value: Any) -> Any:
    """Recursively expand ${ENV_VAR} patterns in config values."""
    if isinstance(value, str):
        # Match ${VAR_NAME} pattern
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, value)
        for var_name in matches:
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

    Args:
        config_path: Path to config file. Defaults to config/providers.yaml

    Returns:
        Parsed and environment-expanded configuration dictionary
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "providers.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Expand environment variables
    return _expand_env_vars(config)


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
        raise ValueError(f"Provider '{active}' not found in config. Available: {list(providers.keys())}")

    provider_cfg = providers[active]

    return ProviderConfig(
        name=active,
        model_id=provider_cfg.get("model_id", ""),
        temperature=provider_cfg.get("temperature", 0.1),
        max_tokens=provider_cfg.get("max_tokens") or provider_cfg.get("max_output_tokens"),
        options=provider_cfg.get("options", {}),
        host=provider_cfg.get("host"),
        api_key=provider_cfg.get("api_key"),
        base_url=provider_cfg.get("base_url"),
        region_name=provider_cfg.get("region_name"),
    )


def get_agent_config(config: dict[str, Any]) -> AgentConfig:
    """Extract agent configuration."""
    agent_cfg = config.get("agent", {})
    return AgentConfig(
        tool_set=agent_cfg.get("tool_set", "reduced"),
        conversation_window=agent_cfg.get("conversation_window", 5),
    )


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

    # -------------------------------------------------------------------------
    # Ollama (Local)
    # -------------------------------------------------------------------------
    if name == "ollama":
        from strands.models.ollama import OllamaModel

        return OllamaModel(
            host=provider_config.host or "http://localhost:11434",
            model_id=provider_config.model_id,
            temperature=provider_config.temperature,
            options=provider_config.options,
        )

    # -------------------------------------------------------------------------
    # Anthropic (Claude)
    # -------------------------------------------------------------------------
    elif name == "anthropic":
        try:
            from strands.models.anthropic import AnthropicModel
        except ImportError:
            raise ImportError(
                "Anthropic provider not installed. Run: uv add 'strands-agents[anthropic]'"
            )

        if not provider_config.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or configure api_key in providers.yaml"
            )

        return AnthropicModel(
            client_args={"api_key": provider_config.api_key},
            model_id=provider_config.model_id,
            max_tokens=provider_config.max_tokens or 4096,
            params={"temperature": provider_config.temperature},
        )

    # -------------------------------------------------------------------------
    # OpenAI (GPT)
    # -------------------------------------------------------------------------
    elif name == "openai":
        try:
            from strands.models.openai import OpenAIModel
        except ImportError:
            raise ImportError(
                "OpenAI provider not installed. Run: uv add 'strands-agents[openai]'"
            )

        if not provider_config.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or configure api_key in providers.yaml"
            )

        client_args: dict[str, Any] = {"api_key": provider_config.api_key}
        if provider_config.base_url:
            client_args["base_url"] = provider_config.base_url

        return OpenAIModel(
            client_args=client_args,
            model_id=provider_config.model_id,
            params={
                "max_tokens": provider_config.max_tokens or 4096,
                "temperature": provider_config.temperature,
            },
        )

    # -------------------------------------------------------------------------
    # AWS Bedrock
    # -------------------------------------------------------------------------
    elif name == "bedrock":
        try:
            from strands.models import BedrockModel
        except ImportError:
            raise ImportError(
                "Bedrock provider not installed. Run: uv add 'strands-agents[bedrock]'"
            )

        kwargs: dict[str, Any] = {
            "model_id": provider_config.model_id,
            "temperature": provider_config.temperature,
        }

        if provider_config.region_name:
            kwargs["region_name"] = provider_config.region_name

        if provider_config.max_tokens:
            kwargs["max_tokens"] = provider_config.max_tokens

        return BedrockModel(**kwargs)

    # -------------------------------------------------------------------------
    # Google Gemini
    # -------------------------------------------------------------------------
    elif name == "gemini":
        try:
            from strands.models.gemini import GeminiModel
        except ImportError:
            raise ImportError(
                "Gemini provider not installed. Run: uv add 'strands-agents[gemini]'"
            )

        if not provider_config.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable "
                "or configure api_key in providers.yaml"
            )

        params: dict[str, Any] = {"temperature": provider_config.temperature}
        if provider_config.max_tokens:
            params["max_output_tokens"] = provider_config.max_tokens

        return GeminiModel(
            client_args={"api_key": provider_config.api_key},
            model_id=provider_config.model_id,
            params=params,
        )

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
