"""
API key management with environment variable and optional .env support.

Design principles:
- Environment variables are the universal interface (works in Docker, Lambda, local)
- .env file support is optional and only for local development convenience
- Lazy loading: keys are read only when requested
- No file-based config storage for secrets
"""

from __future__ import annotations

import os
from typing import Final

# Registry of supported API keys with their environment variable names
# Add new services here as they are integrated
SUPPORTED_KEYS: Final[dict[str, str]] = {
    "gfw": "GFW_API_KEY",  # Global Forest Watch
    "usda_fas": "USDA_FAS_API_KEY",  # USDA Foreign Agricultural Service
    "anthropic": "ANTHROPIC_API_KEY",  # Anthropic Claude
    "openai": "OPENAI_API_KEY",  # OpenAI
    "google": "GOOGLE_API_KEY",  # Google Gemini
    "crossref": "CROSSREF_EMAIL",  # CrossRef API polite pool
    "unpaywall": "UNPAYWALL_EMAIL",  # Unpaywall API
}

# Track whether we've attempted to load .env
_dotenv_loaded: bool = False


def _try_load_dotenv() -> None:
    """Attempt to load .env file if python-dotenv is available.

    This is a no-op if:
    - python-dotenv is not installed (it's an optional dev dependency)
    - .env file doesn't exist
    - Already called once this session
    """
    global _dotenv_loaded

    if _dotenv_loaded:
        return

    _dotenv_loaded = True

    try:
        from dotenv import load_dotenv

        # load_dotenv() returns True if .env was found and loaded
        # It won't override existing environment variables by default
        load_dotenv()
    except ImportError:
        # python-dotenv not installed - this is fine in production
        pass


def get_api_key(service: str) -> str | None:
    """Get an API key for a service from environment variables.

    Attempts to load .env file on first call (if python-dotenv is available).
    Keys are read lazily - only when requested.

    Args:
        service: Service identifier (e.g., "gfw", "anthropic", "openai")
                 Case-insensitive.

    Returns:
        The API key string, or None if not configured.

    Raises:
        ValueError: If the service is not in SUPPORTED_KEYS.

    Example:
        >>> key = get_api_key("gfw")
        >>> if key:
        ...     headers = {"x-api-key": key}
    """
    service_lower = service.lower()

    if service_lower not in SUPPORTED_KEYS:
        supported = ", ".join(sorted(SUPPORTED_KEYS.keys()))
        raise ValueError(
            f"Unknown service: {service!r}. Supported services: {supported}"
        )

    # Try to load .env on first access
    _try_load_dotenv()

    env_var = SUPPORTED_KEYS[service_lower]
    return os.environ.get(env_var)


def list_configured_keys() -> dict[str, bool]:
    """List all supported services and whether they have keys configured.

    Useful for debugging and status reporting.

    Returns:
        Dict mapping service names to whether a key is present.

    Example:
        >>> status = list_configured_keys()
        >>> print(status)
        {'anthropic': True, 'gfw': False, 'google': False, ...}
    """
    # Ensure .env is loaded
    _try_load_dotenv()

    return {
        service: os.environ.get(env_var) is not None
        for service, env_var in sorted(SUPPORTED_KEYS.items())
    }


def require_api_key(service: str) -> str:
    """Get an API key, raising an error if not configured.

    Use this when an API key is required for operation.

    Args:
        service: Service identifier (e.g., "gfw", "anthropic")

    Returns:
        The API key string.

    Raises:
        ValueError: If the service is unknown or key is not configured.

    Example:
        >>> key = require_api_key("gfw")  # Raises if not set
        >>> response = httpx.get(url, headers={"x-api-key": key})
    """
    key = get_api_key(service)

    if key is None:
        env_var = SUPPORTED_KEYS[service.lower()]
        raise ValueError(
            f"API key not configured for {service!r}. "
            f"Set the {env_var} environment variable."
        )

    return key
