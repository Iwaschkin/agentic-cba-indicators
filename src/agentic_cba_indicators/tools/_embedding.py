"""
Shared embedding utilities for Ollama embeddings.

This module provides embedding functions used by both:
- Real-time knowledge base queries (single text)
- Bulk ingestion scripts (batch embedding with fallback)

Supports both local Ollama and Ollama Cloud with TLS validation.
"""

from __future__ import annotations

import os
import time
import warnings
from urllib.parse import urlparse

import httpx

from agentic_cba_indicators.logging_config import get_logger

# Module logger
logger = get_logger(__name__)

# Ollama embedding settings (configurable via environment variables)
# Supports both local Ollama and Ollama Cloud (https://ollama.com)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")  # Optional, for Ollama Cloud
EMBEDDING_MODEL = os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

# Rate limiting for embedding calls (prevents flooding Ollama)
# Default: max 10 calls/second (0.1s between calls)
_MIN_EMBEDDING_INTERVAL = float(os.environ.get("OLLAMA_MIN_INTERVAL", "0.1"))
_last_embedding_time: float = 0.0

# Retry settings for embedding calls
_EMBEDDING_RETRIES = int(os.environ.get("OLLAMA_EMBEDDING_RETRIES", "3"))
_EMBEDDING_BACKOFF = float(os.environ.get("OLLAMA_EMBEDDING_BACKOFF", "1.0"))

# Max characters for embedding (nomic-embed-text has ~8k token limit)
MAX_EMBEDDING_CHARS = int(os.environ.get("OLLAMA_MAX_EMBEDDING_CHARS", "6000"))

# Timeout settings for embedding requests (in seconds)
# Single embedding: 60s default, Batch embedding: 120s default (larger payloads)
_EMBEDDING_TIMEOUT = float(os.environ.get("OLLAMA_EMBEDDING_TIMEOUT", "60.0"))
_BATCH_EMBEDDING_TIMEOUT = float(
    os.environ.get("OLLAMA_BATCH_EMBEDDING_TIMEOUT", "120.0")
)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""


def _validate_ollama_tls() -> None:
    """
    Validate that Ollama connections use TLS when API key is present.

    Warns if HTTP (non-TLS) is used with an API key, except for localhost
    connections which are considered safe for local development.

    Raises:
        UserWarning: If HTTP is used with API key on non-localhost host
    """
    if not OLLAMA_API_KEY:
        return  # No API key, no TLS requirement

    parsed = urlparse(OLLAMA_HOST)
    is_localhost = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    is_http = parsed.scheme == "http"

    if is_http and not is_localhost:
        warnings.warn(
            f"SECURITY WARNING: Ollama API key is set but OLLAMA_HOST ({OLLAMA_HOST}) "
            "uses HTTP instead of HTTPS. This may expose your API key in transit. "
            "Use HTTPS for non-localhost connections or unset OLLAMA_API_KEY.",
            UserWarning,
            stacklevel=2,
        )


def _get_ollama_headers() -> dict[str, str]:
    """Get headers for Ollama API requests, including auth if API key is set."""
    _validate_ollama_tls()  # Check TLS before returning headers with API key
    headers = {"Content-Type": "application/json"}
    if OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
    return headers


def get_embedding(text: str) -> list[float]:
    """Generate embedding for a single text using Ollama (local or cloud).

    Includes rate limiting to prevent flooding the embedding service.
    Rate limit is configurable via OLLAMA_MIN_INTERVAL env var (default: 0.1s).

    Args:
        text: Text to generate embedding for

    Returns:
        List of floats representing the embedding vector

    Raises:
        EmbeddingError: If embedding generation fails after retries
    """
    global _last_embedding_time

    # Rate limiting: ensure minimum interval between calls
    now = time.monotonic()
    elapsed = now - _last_embedding_time
    if elapsed < _MIN_EMBEDDING_INTERVAL:
        time.sleep(_MIN_EMBEDDING_INTERVAL - elapsed)

    last_error: Exception | None = None

    for attempt in range(_EMBEDDING_RETRIES + 1):
        try:
            with httpx.Client(timeout=_EMBEDDING_TIMEOUT) as client:
                response = client.post(
                    f"{OLLAMA_HOST}/api/embed",
                    json={"model": EMBEDDING_MODEL, "input": text},
                    headers=_get_ollama_headers(),
                )
                response.raise_for_status()
                _last_embedding_time = time.monotonic()

                # Parse and validate response
                data = response.json()

                if "embeddings" not in data:
                    raise EmbeddingError(
                        f"Ollama response missing 'embeddings' field. Got keys: {list(data.keys())}"
                    )

                embeddings = data["embeddings"]
                if not embeddings or not isinstance(embeddings, list):
                    raise EmbeddingError(
                        f"Ollama returned empty or invalid embeddings: {type(embeddings)}"
                    )

                embedding = embeddings[0]
                if not embedding or not isinstance(embedding, list):
                    raise EmbeddingError(
                        f"Ollama embedding is empty or invalid: {type(embedding)}"
                    )

                # Validate embedding dimensions (nomic-embed-text is 768-dimensional)
                # Allow some flexibility for other models
                if len(embedding) < 64:
                    raise EmbeddingError(
                        f"Embedding dimension too small: {len(embedding)} (expected >= 64)"
                    )

                return embedding

        except httpx.TimeoutException as e:
            last_error = e
            if attempt < _EMBEDDING_RETRIES:
                delay = _EMBEDDING_BACKOFF * (2**attempt)
                logger.debug(
                    "Embedding timeout (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    _EMBEDDING_RETRIES + 1,
                    delay,
                )
                time.sleep(delay)
                continue
        except httpx.HTTPStatusError as e:
            last_error = e
            # Don't retry on client errors (4xx)
            if 400 <= e.response.status_code < 500:
                raise EmbeddingError(
                    f"Ollama embedding failed (HTTP {e.response.status_code}): {e.response.text[:200]}"
                ) from e
            # Retry on server errors (5xx)
            if attempt < _EMBEDDING_RETRIES:
                delay = _EMBEDDING_BACKOFF * (2**attempt)
                logger.debug(
                    "Embedding server error %d (attempt %d/%d), retrying in %.1fs",
                    e.response.status_code,
                    attempt + 1,
                    _EMBEDDING_RETRIES + 1,
                    delay,
                )
                time.sleep(delay)
                continue
        except (KeyError, IndexError, TypeError) as e:
            # JSON parsing errors - don't retry
            raise EmbeddingError(f"Invalid Ollama response format: {e}") from e

    raise EmbeddingError(
        f"Embedding failed after {_EMBEDDING_RETRIES + 1} attempts: {last_error}"
    )


def get_embeddings_batch(
    texts: list[str], *, strict: bool = False
) -> list[list[float] | None]:
    """Generate embeddings for a batch of texts using Ollama (local or cloud).

    Designed for bulk ingestion with:
    - Automatic text truncation for long documents
    - Fallback to individual embedding if batch fails
    - Optional strict mode that raises on failures

    Args:
        texts: List of texts to generate embeddings for
        strict: If True, raise on any embedding failure; if False, return None for failures

    Returns:
        List of embeddings (or None for failed texts if not strict)

    Raises:
        RuntimeError: If strict=True and any embedding fails
    """
    # Truncate texts that are too long for the embedding model
    truncated_texts = [
        text[:MAX_EMBEDDING_CHARS] + "..." if len(text) > MAX_EMBEDDING_CHARS else text
        for text in texts
    ]

    headers = _get_ollama_headers()
    with httpx.Client(timeout=_BATCH_EMBEDDING_TIMEOUT) as client:
        response = client.post(
            f"{OLLAMA_HOST}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": truncated_texts},
            headers=headers,
        )
        if response.status_code != 200:
            # Fall back to individual embedding if batch fails
            logger.debug(
                "Batch embedding failed (HTTP %d), falling back to individual embedding for %d texts",
                response.status_code,
                len(truncated_texts),
            )
            embeddings: list[list[float] | None] = []
            for i, text in enumerate(truncated_texts):
                try:
                    single_resp = client.post(
                        f"{OLLAMA_HOST}/api/embed",
                        json={"model": EMBEDDING_MODEL, "input": text},
                        headers=headers,
                    )
                    single_resp.raise_for_status()
                    payload = single_resp.json()
                    embeddings.append(payload["embeddings"][0])
                except Exception as e:
                    if strict:
                        raise RuntimeError(
                            f"Embedding failed for doc {i} (len={len(text)})"
                        ) from e
                    logger.debug(
                        "Individual embedding failed for doc %d (len=%d): %s",
                        i,
                        len(text),
                        e,
                    )
                    embeddings.append(None)
            return embeddings

        payload = response.json()
        batch_embeddings = payload.get("embeddings")
        if not isinstance(batch_embeddings, list) or len(batch_embeddings) != len(
            truncated_texts
        ):
            message = "Embedding response invalid or incomplete"
            if strict:
                raise RuntimeError(message)
            return [None] * len(truncated_texts)

        return batch_embeddings
