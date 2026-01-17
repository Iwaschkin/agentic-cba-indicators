"""
Shared HTTP client utilities for external API tools.

Provides consistent error handling, retry logic, and rate limiting
across all external data source integrations.
"""

import json
import os
import random
import re
import time
from typing import Any

import httpx

from agentic_cba_indicators.logging_config import get_logger

# Module logger
logger = get_logger(__name__)

# Default configuration (configurable via environment variables)
DEFAULT_TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "30.0"))
DEFAULT_RETRIES = int(os.environ.get("HTTP_RETRIES", "3"))
DEFAULT_BACKOFF_BASE = float(os.environ.get("HTTP_BACKOFF_BASE", "1.0"))
DEFAULT_BACKOFF_MAX = float(os.environ.get("HTTP_BACKOFF_MAX", "30.0"))
DEFAULT_USER_AGENT = "StrandsCLI/1.0 (CBA-ME-Indicators)"

# Patterns for sensitive data sanitization
_SENSITIVE_PATTERNS = [
    # URL query parameters with sensitive names
    (
        re.compile(
            r"([?&])(api_key|apikey|key|token|secret|password|auth|credential|bearer)=[^&\s]*",
            re.IGNORECASE,
        ),
        r"\1\2=[REDACTED]",
    ),
    # Authorization headers in error messages
    (
        re.compile(r"(Authorization:\s*)(Bearer\s+)?[^\s]+", re.IGNORECASE),
        r"\1[REDACTED]",
    ),
    # Generic API key patterns (32+ char hex/alphanumeric)
    (re.compile(r"\b[a-fA-F0-9]{32,}\b"), "[REDACTED_KEY]"),
]


def sanitize_error(message: str) -> str:
    """
    Remove sensitive information from error messages.

    Sanitizes API keys, tokens, passwords, and other credentials that may
    appear in URLs, headers, or error text.

    Args:
        message: The error message to sanitize

    Returns:
        Sanitized error message with sensitive data replaced by [REDACTED]
    """
    result = message
    for pattern, replacement in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


class APIError(Exception):
    """Custom exception for API errors with status code tracking."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def create_client(
    timeout: float = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    headers: dict[str, str] | None = None,
) -> httpx.Client:
    """
    Create a configured httpx client.

    Args:
        timeout: Request timeout in seconds
        user_agent: User-Agent header for API compliance
        headers: Additional headers to include

    Returns:
        Configured httpx.Client instance
    """
    default_headers = {"User-Agent": user_agent}
    if headers:
        default_headers.update(headers)

    return httpx.Client(timeout=timeout, headers=default_headers)


def fetch_json(
    url: str,
    params: dict[str, Any] | None = None,
    client: httpx.Client | None = None,
    retries: int = DEFAULT_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
) -> dict[str, Any] | list[Any]:
    """
    Fetch JSON from URL with retry logic for rate limiting and transient errors.

    Args:
        url: The URL to fetch
        params: Query parameters
        client: Optional existing httpx client (creates one if not provided)
        retries: Number of retry attempts for 429/5xx errors
        backoff_base: Base delay for exponential backoff (seconds)

    Returns:
        Parsed JSON response

    Raises:
        APIError: On non-recoverable HTTP errors or exhausted retries
    """
    should_close = client is None
    client = client or create_client()

    last_error: Exception | None = None

    try:
        for attempt in range(retries + 1):
            try:
                response = client.get(url, params=params)

                # Success
                if response.status_code == 200:
                    try:
                        return response.json()
                    except json.JSONDecodeError as e:
                        # Don't include raw response body in error (may contain sensitive data)
                        # Sanitize URL to remove any query parameters with sensitive names
                        sanitized_url = sanitize_error(url)
                        raise APIError(
                            f"Invalid JSON response from {sanitized_url}: {e.msg} at line {e.lineno}",
                            status_code=200,
                        ) from e

                # Rate limited - retry with backoff
                if response.status_code == 429:
                    if attempt < retries:
                        # Check for Retry-After header
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            delay = min(float(retry_after), DEFAULT_BACKOFF_MAX)
                        else:
                            base_delay = backoff_base * (2**attempt)
                            jitter = random.uniform(0, backoff_base)
                            delay = min(base_delay + jitter, DEFAULT_BACKOFF_MAX)
                        logger.debug(
                            "Rate limited (429), retrying in %.1fs (attempt %d/%d)",
                            delay,
                            attempt + 1,
                            retries,
                        )
                        time.sleep(delay)
                        continue
                    raise APIError(
                        f"Rate limited (429) after {retries} retries", status_code=429
                    )

                # Server error - retry
                if response.status_code >= 500:
                    if attempt < retries:
                        base_delay = backoff_base * (2**attempt)
                        jitter = random.uniform(0, backoff_base)
                        delay = min(base_delay + jitter, DEFAULT_BACKOFF_MAX)
                        logger.debug(
                            "Server error (%d), retrying in %.1fs (attempt %d/%d)",
                            response.status_code,
                            delay,
                            attempt + 1,
                            retries,
                        )
                        time.sleep(delay)
                        continue
                    raise APIError(
                        f"Server error ({response.status_code}) after {retries} retries",
                        status_code=response.status_code,
                    )

                # Client error - don't retry
                raise APIError(
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    status_code=response.status_code,
                )

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < retries:
                    base_delay = backoff_base * (2**attempt)
                    jitter = random.uniform(0, backoff_base)
                    delay = min(base_delay + jitter, DEFAULT_BACKOFF_MAX)
                    logger.debug(
                        "Request timeout, retrying in %.1fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        retries,
                    )
                    time.sleep(delay)
                    continue
                raise APIError(f"Request timeout after {retries} retries") from e

            except httpx.RequestError as e:
                last_error = e
                if attempt < retries:
                    base_delay = backoff_base * (2**attempt)
                    jitter = random.uniform(0, backoff_base)
                    delay = min(base_delay + jitter, DEFAULT_BACKOFF_MAX)
                    logger.debug(
                        "Request error (%s), retrying in %.1fs (attempt %d/%d)",
                        type(e).__name__,
                        delay,
                        attempt + 1,
                        retries,
                    )
                    time.sleep(delay)
                    continue
                raise APIError(f"Request failed: {e!s}") from e

        # Should not reach here, but just in case
        raise APIError(f"Unexpected error: {last_error}")

    finally:
        if should_close:
            client.close()


def format_error(error: Exception, context: str = "") -> str:
    """
    Format an error for user-friendly display.

    Automatically sanitizes sensitive information like API keys from
    the error message to prevent credential leakage.

    Args:
        error: The exception to format
        context: Additional context about what operation failed

    Returns:
        Formatted and sanitized error message string
    """
    prefix = f"Error {context}: " if context else "Error: "

    if isinstance(error, APIError):
        if error.status_code:
            return f"{prefix}HTTP {error.status_code} - {sanitize_error(str(error))}"
        return f"{prefix}{sanitize_error(str(error))}"

    return f"{prefix}{sanitize_error(str(error))}"
