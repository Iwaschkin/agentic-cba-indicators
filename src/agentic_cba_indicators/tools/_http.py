"""
Shared HTTP client utilities for external API tools.

Provides consistent error handling, retry logic, and rate limiting
across all external data source integrations.

Thread Safety:
    The TTL cache for API responses uses cachetools.TTLCache with a
    threading.Lock to ensure thread-safe access in multi-threaded contexts.
"""

import hashlib
import json
import os
import random
import re
import threading
import time
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

import httpx
from cachetools import TTLCache

from agentic_cba_indicators.logging_config import get_logger

# Module logger
logger = get_logger(__name__)

# Type variable for generic decorator
F = TypeVar("F", bound=Callable[..., Any])

# Default configuration (configurable via environment variables)
DEFAULT_TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "30.0"))
DEFAULT_RETRIES = int(os.environ.get("HTTP_RETRIES", "3"))
DEFAULT_BACKOFF_BASE = float(os.environ.get("HTTP_BACKOFF_BASE", "1.0"))
DEFAULT_BACKOFF_MAX = float(os.environ.get("HTTP_BACKOFF_MAX", "30.0"))
DEFAULT_USER_AGENT = "StrandsCLI/1.0 (CBA-ME-Indicators)"

# Cache configuration
DEFAULT_CACHE_TTL = int(os.environ.get("API_CACHE_TTL", "3600"))  # 1 hour
DEFAULT_CACHE_MAXSIZE = int(os.environ.get("API_CACHE_MAXSIZE", "1000"))

# Global TTL cache for API responses (thread-safe)
_api_cache: TTLCache[str, Any] = TTLCache(
    maxsize=DEFAULT_CACHE_MAXSIZE, ttl=DEFAULT_CACHE_TTL
)
_cache_lock = threading.Lock()

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


class ErrorCategory(str, Enum):
    """High-level error categories for tool failures."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


def classify_error(error: Exception) -> ErrorCategory:
    """Classify errors into coarse categories for diagnostics and retries."""
    if isinstance(error, APIError):
        status = error.status_code
        if status == 429:
            return ErrorCategory.RATE_LIMIT
        if status in {408, 425}:
            return ErrorCategory.TRANSIENT
        if status is not None and 500 <= status <= 599:
            return ErrorCategory.TRANSIENT
        if status is not None and 400 <= status <= 499:
            return ErrorCategory.PERMANENT
        return ErrorCategory.UNKNOWN

    if isinstance(error, httpx.TimeoutException):
        return ErrorCategory.TRANSIENT

    if isinstance(error, ValueError):
        return ErrorCategory.VALIDATION

    return ErrorCategory.UNKNOWN


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
    assert client is not None  # Guaranteed by line above

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
    category = classify_error(error).value
    prefix = (
        f"Error {context} (category: {category}): "
        if context
        else f"Error (category: {category}): "
    )

    if isinstance(error, APIError):
        if error.status_code:
            return f"{prefix}HTTP {error.status_code} - {sanitize_error(str(error))}"
        return f"{prefix}{sanitize_error(str(error))}"

    return f"{prefix}{sanitize_error(str(error))}"


# =============================================================================
# API Response Caching
# =============================================================================


def _make_cache_key(url: str, params: dict[str, Any] | None = None) -> str:
    """Generate a cache key from URL and query parameters.

    Args:
        url: The request URL
        params: Query parameters dictionary

    Returns:
        SHA256 hash of normalized URL + params for consistent key generation
    """
    # Normalize params to sorted JSON for consistent hashing
    params_str = json.dumps(params, sort_keys=True) if params else ""
    key_data = f"{url}|{params_str}"
    return hashlib.sha256(key_data.encode()).hexdigest()


def fetch_json_cached(
    url: str,
    params: dict[str, Any] | None = None,
    client: httpx.Client | None = None,
    retries: int = DEFAULT_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    use_cache: bool = True,
) -> dict[str, Any] | list[Any]:
    """
    Fetch JSON from URL with caching and retry logic.

    Wraps fetch_json with TTL-based caching for repeated requests.
    Cache is thread-safe and shared across tool invocations.

    Args:
        url: The URL to fetch
        params: Query parameters
        client: Optional existing httpx client (creates one if not provided)
        retries: Number of retry attempts for 429/5xx errors
        backoff_base: Base delay for exponential backoff (seconds)
        use_cache: Whether to use caching (default True)

    Returns:
        Parsed JSON response (from cache if available)

    Raises:
        APIError: On non-recoverable HTTP errors or exhausted retries
    """
    if not use_cache:
        return fetch_json(url, params, client, retries, backoff_base)

    cache_key = _make_cache_key(url, params)

    # Check cache (thread-safe read)
    with _cache_lock:
        if cache_key in _api_cache:
            logger.debug("Cache hit for %s", url[:80])
            return _api_cache[cache_key]

    # Cache miss - fetch from API
    logger.debug("Cache miss for %s", url[:80])
    result = fetch_json(url, params, client, retries, backoff_base)

    # Store in cache (thread-safe write)
    with _cache_lock:
        _api_cache[cache_key] = result

    return result


def cached_api_call(
    ttl: int | None = None,
    maxsize: int | None = None,
) -> Callable[[F], F]:
    """
    Decorator for caching API call results with TTL.

    Creates a dedicated cache per decorated function with configurable
    TTL and size limits. Useful for functions that make API calls with
    hashable arguments.

    Args:
        ttl: Time-to-live in seconds (default: DEFAULT_CACHE_TTL)
        maxsize: Maximum cache size (default: 100)

    Returns:
        Decorator function

    Example:
        @cached_api_call(ttl=3600)
        def get_country_data(country_code: str) -> dict:
            return fetch_json(f"https://api.example.com/countries/{country_code}")

    Note:
        - Only works with hashable arguments
        - Cache is local to each decorated function
        - Thread-safe via lock
    """
    actual_ttl = ttl or DEFAULT_CACHE_TTL
    actual_maxsize = maxsize or 100

    def decorator(func: F) -> F:
        # Create per-function cache and lock
        cache: TTLCache[str, Any] = TTLCache(maxsize=actual_maxsize, ttl=actual_ttl)
        lock = threading.Lock()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key from function name + args + kwargs
            try:
                key_data = json.dumps(
                    {"args": args, "kwargs": kwargs}, sort_keys=True, default=str
                )
            except (TypeError, ValueError):
                # If args aren't JSON-serializable, don't cache
                logger.debug(
                    "Cannot cache %s: non-serializable arguments", func.__name__
                )
                return func(*args, **kwargs)

            cache_key = hashlib.sha256(key_data.encode()).hexdigest()

            # Check cache
            with lock:
                if cache_key in cache:
                    logger.debug("Cache hit for %s", func.__name__)
                    return cache[cache_key]

            # Cache miss - call function
            logger.debug("Cache miss for %s", func.__name__)
            result = func(*args, **kwargs)

            # Store in cache
            with lock:
                cache[cache_key] = result

            return result

        # Expose cache for testing/inspection
        wrapper.cache = cache  # type: ignore[attr-defined]
        wrapper.cache_clear = lambda: cache.clear()  # type: ignore[attr-defined]

        return wrapper  # type: ignore[return-value]

    return decorator


def get_cache_stats() -> dict[str, Any]:
    """Get statistics about the global API response cache.

    Returns:
        Dictionary with cache statistics including:
        - size: Current number of cached items
        - maxsize: Maximum cache size
        - ttl: Time-to-live in seconds
    """
    with _cache_lock:
        return {
            "size": len(_api_cache),
            "maxsize": _api_cache.maxsize,
            "ttl": _api_cache.ttl,
        }


def clear_api_cache() -> int:
    """Clear the global API response cache.

    Returns:
        Number of items cleared from cache
    """
    with _cache_lock:
        count = len(_api_cache)
        _api_cache.clear()
        logger.info("Cleared %d items from API cache", count)
        return count
