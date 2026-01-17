"""
Shared HTTP client utilities for external API tools.

Provides consistent error handling, retry logic, and rate limiting
across all external data source integrations.
"""

import time
from typing import Any

import httpx

# Default configuration
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.0
DEFAULT_USER_AGENT = "StrandsCLI/1.0 (CBA-ME-Indicators)"


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
                    return response.json()

                # Rate limited - retry with backoff
                if response.status_code == 429:
                    if attempt < retries:
                        # Check for Retry-After header
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            delay = float(retry_after)
                        else:
                            delay = backoff_base * (2**attempt)
                        time.sleep(delay)
                        continue
                    raise APIError(
                        f"Rate limited (429) after {retries} retries", status_code=429
                    )

                # Server error - retry
                if response.status_code >= 500:
                    if attempt < retries:
                        delay = backoff_base * (2**attempt)
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
                    delay = backoff_base * (2**attempt)
                    time.sleep(delay)
                    continue
                raise APIError(f"Request timeout after {retries} retries") from e

            except httpx.RequestError as e:
                last_error = e
                if attempt < retries:
                    delay = backoff_base * (2**attempt)
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

    Args:
        error: The exception to format
        context: Additional context about what operation failed

    Returns:
        Formatted error message string
    """
    prefix = f"Error {context}: " if context else "Error: "

    if isinstance(error, APIError):
        if error.status_code:
            return f"{prefix}HTTP {error.status_code} - {error!s}"
        return f"{prefix}{error!s}"

    return f"{prefix}{error!s}"
